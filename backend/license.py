"""Lemon Squeezy license keys — Free (1 MT5 account) vs Pro (unlimited).

Uses the public License API (no Lemon Squeezy secret required):

    POST https://api.lemonsqueezy.com/v1/licenses/activate
    POST https://api.lemonsqueezy.com/v1/licenses/validate
    POST https://api.lemonsqueezy.com/v1/licenses/deactivate

Persistence lives in the same SQLite file as the rest of Atlas (`atlas.db`),
in the `atlas_license` table. The table is created with
`CREATE TABLE IF NOT EXISTS`. The `instance_id` column is added with
`ALTER TABLE ... ADD COLUMN` only when it is missing. The table is never
dropped or recreated.

The license key is stored locally so it can be revalidated, but it is never
returned by the API, written to reports, or included in log messages — the
same scrub discipline used for MT5 passwords and bridge tokens.

Activation is registered per PC (`instance_name` is a stable hash, not a
personal identifier). Revalidation sends that `instance_id` and runs at most
once per day. If the remote call fails (no network, timeouts, 5xx), the last
successful *valid* check is honoured for 7 days. An explicit refusal never
uses that grace period.

`LEMON_STORE_ID` and `LEMON_PRODUCT_ID` are module constants (0 until the
founder sets the real ids). Customer PCs do not read them from the
environment. Tests and development may override. The store/product check is
skipped only while both are 0. If only one is set, Pro is not granted and
the misconfiguration is logged once.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import httpx

logger = logging.getLogger("atlas.license")

LEMON_ACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/activate"
LEMON_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
LEMON_DEACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/deactivate"
FREE_ACCOUNT_LIMIT = 1
REVALIDATE_AFTER = timedelta(days=1)
GRACE_AFTER_VALID = timedelta(days=7)
HTTP_TIMEOUT_SEC = 8.0
_INSTANCE_PREFIX = "atlas-"
_INSTANCE_HASH_LEN = 32

# Singleton row id — one license per installation.
_ROW_ID = 1

_STATUS_FREE = "free"
_STATUS_PRO_ACTIVE = "pro_active"
_STATUS_PRO_EXPIRED = "pro_expired"
_STATUS_CHECKING = "checking"

_REFUSAL_EXPIRED = "expired"
_REFUSAL_DISABLED = "disabled"
_REFUSAL_LIMIT = "activation_limit"
_REFUSAL_WRONG_STORE = "wrong_store"
_REFUSAL_WRONG_PRODUCT = "wrong_product"
_REFUSAL_UNKNOWN_INSTANCE = "unknown_instance"
_REFUSAL_INVALID = "invalid"
_REFUSAL_MISCONFIGURED = "misconfigured"

FREE_LIMIT_MESSAGE = (
    "The free version includes 1 MT5 account. "
    "To connect more accounts, paste your Pro license key in Settings → License."
)
INVALID_KEY_MESSAGE = (
    "This license key could not be validated. "
    "Atlas stays on the free version (1 MT5 account)."
)
NETWORK_ACTIVATE_MESSAGE = (
    "Could not reach the license server. Check your internet connection and try again."
)
PRO_ACTIVE_MESSAGE = "Pro license active. You can connect unlimited MT5 accounts."
PRO_EXPIRED_MESSAGE = (
    "This Pro license has expired. Atlas is back on the free version (1 MT5 account)."
)
DISABLED_KEY_MESSAGE = (
    "This license key is disabled. Atlas is back on the free version (1 MT5 account)."
)
ACTIVATION_LIMIT_MESSAGE = (
    "This key is already active on another PC. Deactivate it there or contact support."
)
WRONG_STORE_MESSAGE = (
    "This license key is not from the Sr Atlas store. "
    "Atlas stays on the free version (1 MT5 account)."
)
WRONG_PRODUCT_MESSAGE = (
    "This license key is not for Sr Atlas Pro. "
    "Atlas stays on the free version (1 MT5 account)."
)
UNKNOWN_INSTANCE_MESSAGE = (
    "This license is not active on this PC. "
    "Activate it again, or deactivate it on the other PC."
)
DEACTIVATED_MESSAGE = (
    "Pro license deactivated on this PC. "
    "Atlas is back on the free version (1 MT5 account)."
)
DIFFERENT_KEY_MESSAGE = (
    "Deactivate the current license on this PC first "
    "(Settings → License → Deactivate on this PC)."
)
FREE_MESSAGE = "Free version: 1 MT5 account."
CHECKING_MESSAGE = "Checking license status…"
CACHED_PRO_MESSAGE = (
    "Pro license active (using the last successful check — the license server "
    "could not be reached just now)."
)
_STORE_UNCONFIGURED_WARNING = (
    "LEMON_STORE_ID and LEMON_PRODUCT_ID are 0; store and product check is skipped."
)
_STORE_PARTIAL_WARNING = (
    "LEMON_STORE_ID or LEMON_PRODUCT_ID is set while the other is 0; "
    "partial license configuration is a mismatch and Pro is not granted."
)
MISCONFIGURED_MESSAGE = (
    "License server configuration is incomplete. "
    "Atlas stays on the free version (1 MT5 account)."
)

_REFUSAL_MESSAGES = {
    _REFUSAL_EXPIRED: PRO_EXPIRED_MESSAGE,
    _REFUSAL_DISABLED: DISABLED_KEY_MESSAGE,
    _REFUSAL_LIMIT: ACTIVATION_LIMIT_MESSAGE,
    _REFUSAL_WRONG_STORE: WRONG_STORE_MESSAGE,
    _REFUSAL_WRONG_PRODUCT: WRONG_PRODUCT_MESSAGE,
    _REFUSAL_UNKNOWN_INSTANCE: UNKNOWN_INSTANCE_MESSAGE,
    _REFUSAL_INVALID: INVALID_KEY_MESSAGE,
    _REFUSAL_MISCONFIGURED: MISCONFIGURED_MESSAGE,
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS atlas_license (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    license_key TEXT NOT NULL DEFAULT '',
    valid INTEGER NOT NULL DEFAULT 0,
    lemon_status TEXT,
    last_verified_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    updated_at TEXT,
    instance_id TEXT,
    prev_license_key TEXT,
    prev_instance_id TEXT
);
"""

# instance_id is used. prev_* were added earlier and stay unused. Never drop them.
_ADDITIVE_COLUMNS = ("instance_id", "prev_license_key", "prev_instance_id")

_lock = threading.Lock()
_store_config_warnings_logged: set[str] = set()

# UUID-shaped Lemon keys and explicit "license_key=..." assignments.
_KEY_ASSIGNMENT_RE = re.compile(
    r"(?i)(license[_-]?key)([\"']?\s*[:=]\s*[\"']?)([^\s\"',;]+)"
)


class LicenseError(Exception):
    """Base class for license failures that are safe to show to the user."""


class LicenseInvalidError(LicenseError):
    pass


class LicenseNetworkError(LicenseError):
    pass


class AccountLimitError(ValueError):
    """Raised when a Free installation would exceed 1 simultaneous MT5 account."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


# Baked in. 0 until the founder supplies the real Lemon Squeezy ids.
LEMON_STORE_ID = 0
LEMON_PRODUCT_ID = 0
_DEV_OVERRIDE_MODES = frozenset({"dev", "development", "test"})


def _env_int(name: str) -> int:
    raw = (os.environ.get(name) or "0").strip()
    try:
        value = int(raw)
    except ValueError:
        return 0
    return value if value > 0 else 0


def _license_id_override_allowed() -> bool:
    """Customer installations use the constants. Tests and dev may override."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    mode = (os.environ.get("ATLAS_ENV") or "").strip().lower()
    return mode in _DEV_OVERRIDE_MODES


def _configured_id(constant: int, env_name: str) -> int:
    if _license_id_override_allowed() and env_name in os.environ:
        return _env_int(env_name)
    return constant if constant > 0 else 0


def lemon_store_id() -> int:
    """Store id used for the match. Constant, unless tests or dev override."""
    return _configured_id(LEMON_STORE_ID, "LEMON_STORE_ID")


def lemon_product_id() -> int:
    """Product id used for the match. Constant, unless tests or dev override."""
    return _configured_id(LEMON_PRODUCT_ID, "LEMON_PRODUCT_ID")


def _warn_store_config_once(kind: str, message: str) -> None:
    if kind in _store_config_warnings_logged:
        return
    _store_config_warnings_logged.add(kind)
    logger.warning(message)


def _note_store_config() -> str:
    """Return skip, fail, or check.

    The match is skipped only when both ids are 0. One configured id is a
    mismatch: Pro is not granted, and the misconfiguration is logged once.
    """
    store = lemon_store_id()
    product = lemon_product_id()
    if store == 0 and product == 0:
        _warn_store_config_once("unconfigured", _STORE_UNCONFIGURED_WARNING)
        return "skip"
    if store == 0 or product == 0:
        _warn_store_config_once("partial", _STORE_PARTIAL_WARNING)
        return "fail"
    return "check"


def _machine_material() -> str:
    """Stable machine material. Windows MachineGuid, else the MAC node id.

    The raw value is hashed before it leaves the machine.
    """
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                value, _typ = winreg.QueryValueEx(key, "MachineGuid")
            guid = str(value or "").strip()
            if guid:
                return guid
        except Exception:
            logger.warning("MachineGuid unreadable; using the local node id")
    return str(uuid.getnode())


def machine_instance_name() -> str:
    """Stable PC label for Lemon: `atlas-` plus a truncated SHA-256."""
    digest = hashlib.sha256(_machine_material().encode("utf-8")).hexdigest()
    return _INSTANCE_PREFIX + digest[:_INSTANCE_HASH_LEN]


def _data_dir() -> Path:
    explicit = os.environ.get("ATLAS_DATA_DIR")
    if explicit:
        d = Path(explicit)
    else:
        sqlite_path = os.environ.get("ATLAS_SQLITE_PATH")
        d = Path(sqlite_path).parent if sqlite_path else (Path(__file__).parent / "data")
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    explicit = os.environ.get("ATLAS_SQLITE_PATH")
    if explicit:
        p = Path(explicit)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return _data_dir() / "atlas.db"


def scrub(text: Optional[str], extra_secrets: Iterable[str] = ()) -> str:
    """Strip license keys (and any extra secrets) from a string.

    Safe to use on log lines, stored error text, and serialized API payloads.
    """
    if text is None:
        return ""
    out = str(text)
    for secret in extra_secrets:
        if secret:
            out = out.replace(str(secret), "[redacted]")
    out = _KEY_ASSIGNMENT_RE.sub(r"\1\2[redacted]", out)
    return out


def _log_warning(msg: str, *args: Any, extra_secrets: Iterable[str] = ()) -> None:
    logger.warning(scrub(msg % args if args else msg, extra_secrets))


@contextmanager
def _cx(path: Optional[Path] = None):
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(str(p), isolation_level=None, timeout=5.0)
    cx.row_factory = sqlite3.Row
    try:
        yield cx
    finally:
        cx.close()


def ensure_schema(path: Optional[Path] = None) -> None:
    with _cx(path) as cx:
        cx.executescript(_SCHEMA)
        cols = {row[1] for row in cx.execute("PRAGMA table_info(atlas_license)")}
        for name in _ADDITIVE_COLUMNS:
            if name in cols:
                continue
            try:
                cx.execute(f"ALTER TABLE atlas_license ADD COLUMN {name} TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc).lower():
                    raise


def _empty_row() -> dict:
    return {
        "license_key": "",
        "valid": 0,
        "lemon_status": None,
        "last_verified_at": None,
        "last_success_at": None,
        "last_error": None,
        "updated_at": None,
        "instance_id": "",
    }


def _row_to_dict(row: sqlite3.Row | None) -> dict:
    if row is None:
        return _empty_row()
    keys = set(row.keys())

    def _text(name: str) -> str:
        if name not in keys:
            return ""
        return row[name] or ""

    return {
        "license_key": row["license_key"] or "",
        "valid": int(row["valid"] or 0),
        "lemon_status": row["lemon_status"],
        "last_verified_at": row["last_verified_at"],
        "last_success_at": row["last_success_at"],
        "last_error": row["last_error"],
        "updated_at": row["updated_at"],
        "instance_id": _text("instance_id"),
    }


def load_record(path: Optional[Path] = None) -> dict:
    ensure_schema(path)
    with _cx(path) as cx:
        row = cx.execute(
            "SELECT license_key, valid, lemon_status, last_verified_at, "
            "last_success_at, last_error, updated_at, instance_id "
            "FROM atlas_license WHERE id=?",
            (_ROW_ID,),
        ).fetchone()
    return _row_to_dict(row)


def _save_record(record: dict, path: Optional[Path] = None) -> None:
    ensure_schema(path)
    key = record.get("license_key") or ""
    with _cx(path) as cx:
        cx.execute(
            "INSERT INTO atlas_license "
            "(id, license_key, valid, lemon_status, last_verified_at, "
            " last_success_at, last_error, updated_at, instance_id) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            " license_key=excluded.license_key,"
            " valid=excluded.valid,"
            " lemon_status=excluded.lemon_status,"
            " last_verified_at=excluded.last_verified_at,"
            " last_success_at=excluded.last_success_at,"
            " last_error=excluded.last_error,"
            " updated_at=excluded.updated_at,"
            " instance_id=excluded.instance_id",
            (
                _ROW_ID,
                key,
                1 if record.get("valid") else 0,
                record.get("lemon_status"),
                record.get("last_verified_at"),
                record.get("last_success_at"),
                scrub(record.get("last_error"), extra_secrets=[key]),
                record.get("updated_at") or _now_iso(),
                record.get("instance_id") or "",
            ),
        )


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _fresh_enough(ts: Optional[datetime], window: timedelta) -> bool:
    if ts is None:
        return False
    return _now() - ts <= window


def _network_result() -> dict:
    return {
        "network_error": True,
        "valid": False,
        "deactivated": False,
        "lemon_status": None,
        "instance_id": None,
        "error": NETWORK_ACTIVATE_MESSAGE,
        "refusal": None,
    }


def _refusal_result(refusal: str, instance_id: str = "") -> dict:
    return {
        "network_error": False,
        "valid": False,
        "deactivated": False,
        "lemon_status": refusal,
        "instance_id": instance_id or "",
        "error": _REFUSAL_MESSAGES.get(refusal, INVALID_KEY_MESSAGE),
        "refusal": refusal,
    }


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _meta_ids(payload: dict) -> tuple[int, int]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    return _as_int(meta.get("store_id")), _as_int(meta.get("product_id"))


def _instance_id_from(payload: dict) -> str:
    inst = payload.get("instance")
    if isinstance(inst, dict) and inst.get("id"):
        return str(inst.get("id")).strip()
    return ""


def _classify_refusal(payload: dict, info: dict) -> str:
    status = str((info or {}).get("status") or "").strip().lower()
    error_l = str(payload.get("error") or "").lower()
    if status == "expired" or "has expired" in error_l or "is expired" in error_l:
        return _REFUSAL_EXPIRED
    if status == "disabled" or "disabled" in error_l:
        return _REFUSAL_DISABLED
    if "activation limit" in error_l:
        return _REFUSAL_LIMIT
    if "instance" in error_l:
        return _REFUSAL_UNKNOWN_INSTANCE
    return _REFUSAL_INVALID


def _store_product_refusal(payload: dict) -> Optional[str]:
    mode = _note_store_config()
    if mode == "skip":
        return None
    if mode == "fail":
        return _REFUSAL_MISCONFIGURED
    got_store, got_product = _meta_ids(payload)
    if got_store != lemon_store_id():
        return _REFUSAL_WRONG_STORE
    if got_product != lemon_product_id():
        return _REFUSAL_WRONG_PRODUCT
    return None


def _interpret(payload: Any, mode: str) -> dict:
    if not isinstance(payload, dict):
        return _refusal_result(_REFUSAL_INVALID)
    info = payload.get("license_key") if isinstance(payload.get("license_key"), dict) else {}
    status = str(info.get("status") or "").strip().lower()
    instance_id = _instance_id_from(payload)

    if mode == "deactivate":
        if bool(payload.get("deactivated")):
            return {
                "network_error": False,
                "valid": False,
                "deactivated": True,
                "lemon_status": "inactive",
                "instance_id": "",
                "error": None,
                "refusal": None,
            }
        refusal = _classify_refusal(payload, info)
        result = _refusal_result(refusal, instance_id)
        result["deactivated"] = False
        return result

    if mode == "activate":
        accepted = bool(payload.get("activated")) and status == "active" and bool(instance_id)
    else:
        accepted = bool(payload.get("valid")) and status == "active"

    if accepted:
        store_refusal = _store_product_refusal(payload)
        if store_refusal:
            return _refusal_result(store_refusal, instance_id)
        return {
            "network_error": False,
            "valid": True,
            "deactivated": False,
            "lemon_status": "active",
            "instance_id": instance_id,
            "error": None,
            "refusal": None,
        }

    # Still note an unconfigured or partial store check, including on a refusal, once.
    _note_store_config()
    return _refusal_result(_classify_refusal(payload, info), instance_id)


def _post_lemon(url: str, form: dict) -> tuple[Any, Optional[dict]]:
    """POST a license form. Returns (payload, network_result).

    `network_result` is set on transport failure, HTTP ≥ 500, or non-JSON.
    The license key is never written to the log.
    """
    try:
        response = httpx.post(
            url,
            data=form,
            headers={"Accept": "application/json"},
            timeout=HTTP_TIMEOUT_SEC,
        )
    except httpx.RequestError as exc:
        _log_warning("Lemon Squeezy request failed (%s)", type(exc).__name__)
        return None, _network_result()

    if response.status_code >= 500:
        _log_warning("Lemon Squeezy request returned HTTP %s", response.status_code)
        return None, _network_result()

    try:
        payload = response.json()
    except ValueError:
        _log_warning(
            "Lemon Squeezy request returned non-JSON (HTTP %s)", response.status_code
        )
        return None, _network_result()
    return payload, None


def validate_with_lemon(license_key: str, instance_id: str = "") -> dict:
    """Call Lemon Squeezy validate. Never logs or returns the raw key.

    Sends `instance_id` when this PC already has one.
    """
    key = (license_key or "").strip()
    if not key:
        return _refusal_result(_REFUSAL_INVALID)
    form = {"license_key": key}
    instance = (instance_id or "").strip()
    if instance:
        form["instance_id"] = instance
    payload, network = _post_lemon(LEMON_VALIDATE_URL, form)
    if network is not None:
        return network
    return _interpret(payload, "validate")


def activate_with_lemon(license_key: str) -> dict:
    """Register this PC with Lemon Squeezy. Never logs the raw key."""
    key = (license_key or "").strip()
    if not key:
        return _refusal_result(_REFUSAL_INVALID)
    payload, network = _post_lemon(
        LEMON_ACTIVATE_URL,
        {"license_key": key, "instance_name": machine_instance_name()},
    )
    if network is not None:
        return network
    return _interpret(payload, "activate")


def deactivate_with_lemon(license_key: str, instance_id: str) -> dict:
    """Release this PC's instance. Never logs the raw key."""
    key = (license_key or "").strip()
    instance = (instance_id or "").strip()
    if not key or not instance:
        return _refusal_result(_REFUSAL_INVALID)
    payload, network = _post_lemon(
        LEMON_DEACTIVATE_URL,
        {"license_key": key, "instance_id": instance},
    )
    if network is not None:
        return network
    return _interpret(payload, "deactivate")


def _release_instance(key: str, instance_id: str) -> None:
    """Best-effort remote release after a store/product rejection.

    A network failure here does not grant Pro. The key is not logged.
    """
    if not key or not instance_id:
        return
    _payload, network = _post_lemon(
        LEMON_DEACTIVATE_URL,
        {"license_key": key, "instance_id": instance_id},
    )
    if network is not None:
        _log_warning("Could not release a rejected license instance (network)")


def _keep_instance(result: dict, instance_id: str) -> dict:
    """Keep the stored instance unless Lemon says that instance is gone."""
    if result.get("refusal") == _REFUSAL_UNKNOWN_INSTANCE:
        result = dict(result)
        result["instance_id"] = ""
        return result
    if instance_id and not (result.get("instance_id") or "").strip():
        result = dict(result)
        result["instance_id"] = instance_id
    return result


def _apply_remote_result(record: dict, key: str, result: dict) -> dict:
    now = _now_iso()
    record = dict(record)
    record["license_key"] = key
    record["updated_at"] = now
    record["last_error"] = scrub(result.get("error"), extra_secrets=[key])
    # Always stamp last_verified_at so we do not retry the API more than
    # once a day — including after a network failure. Pro-ness itself is
    # decided from last_success_at (7-day grace), not from this stamp.
    record["last_verified_at"] = now
    if result.get("network_error"):
        # Keep previous valid / last_success_at / instance_id.
        return record
    record["valid"] = 1 if result.get("valid") else 0
    record["lemon_status"] = result.get("lemon_status")
    if result.get("valid"):
        record["last_success_at"] = now
    if result.get("instance_id") is not None:
        record["instance_id"] = result.get("instance_id") or ""
    return record


def _reject_foreign_activation(key: str, result: dict) -> dict:
    if result.get("refusal") in (
        _REFUSAL_WRONG_STORE, _REFUSAL_WRONG_PRODUCT, _REFUSAL_MISCONFIGURED,
    ):
        instance_id = (result.get("instance_id") or "").strip()
        if instance_id:
            _release_instance(key, instance_id)
            result = dict(result)
            result["instance_id"] = ""
    return result


def _refresh_if_due(record: dict) -> dict:
    """Revalidate at most once per day. Honour 7-day grace on network failure."""
    key = (record.get("license_key") or "").strip()
    if not key:
        return record
    last_verified = _parse_iso(record.get("last_verified_at"))
    if _fresh_enough(last_verified, REVALIDATE_AFTER):
        return record
    with _lock:
        # Re-read after acquiring the lock — another thread may have just refreshed.
        record = load_record()
        key = (record.get("license_key") or "").strip()
        if not key:
            return record
        last_verified = _parse_iso(record.get("last_verified_at"))
        if _fresh_enough(last_verified, REVALIDATE_AFTER):
            return record
        instance_id = (record.get("instance_id") or "").strip()
        if instance_id:
            result = _keep_instance(validate_with_lemon(key, instance_id), instance_id)
        elif record.get("valid") and record.get("lemon_status") in (None, "active"):
            # Saved before per-PC activation existed. Register this PC once.
            result = _reject_foreign_activation(key, activate_with_lemon(key))
        else:
            return record
        record = _apply_remote_result(record, key, result)
        _save_record(record)
        return record


def _compute_status(record: dict) -> str:
    key = (record.get("license_key") or "").strip()
    if not key:
        return _STATUS_FREE
    last_verified = _parse_iso(record.get("last_verified_at"))
    last_success = _parse_iso(record.get("last_success_at"))
    lemon_status = record.get("lemon_status")
    is_valid = bool(record.get("valid"))
    success_in_grace = _fresh_enough(last_success, GRACE_AFTER_VALID)

    # A confirmed non-Pro answer is an explicit refusal. The 7-day grace
    # applies only while `valid` is still the last successful check, which
    # is what a network failure leaves behind.
    if not is_valid and last_verified is not None:
        if lemon_status == "expired":
            return _STATUS_PRO_EXPIRED
        return _STATUS_FREE
    if is_valid and success_in_grace:
        return _STATUS_PRO_ACTIVE
    if is_valid and not success_in_grace:
        return _STATUS_FREE
    if last_verified is None:
        return _STATUS_CHECKING
    return _STATUS_FREE


def _using_cache(record: dict, status: str) -> bool:
    if status != _STATUS_PRO_ACTIVE:
        return False
    last_success = _parse_iso(record.get("last_success_at"))
    if last_success is None:
        return False
    return not _fresh_enough(last_success, REVALIDATE_AFTER)


def is_pro_active() -> bool:
    record = _refresh_if_due(load_record())
    return _compute_status(record) == _STATUS_PRO_ACTIVE


def max_accounts() -> Optional[int]:
    """None means unlimited (Pro)."""
    return None if is_pro_active() else FREE_ACCOUNT_LIMIT


def can_use_n_accounts(n: int) -> bool:
    limit = max_accounts()
    return limit is None or n <= limit


def enforce_account_limit(desired_count: int) -> None:
    """Raise AccountLimitError if `desired_count` exceeds the current license."""
    if desired_count <= 0:
        return
    if not can_use_n_accounts(desired_count):
        raise AccountLimitError(FREE_LIMIT_MESSAGE)


def _configured_account_count() -> int:
    """Best-effort count of simultaneous MT5 slots (dashboard + env URLs)."""
    n = 0
    try:
        import mt5_config as _mt5cfg

        if _mt5cfg.load().get("configured"):
            n = 1
    except Exception:
        pass
    try:
        import mt5_client as _mt5client

        n = max(n, len(_mt5client.configured_bridges()))
    except Exception:
        pass
    return n


def _message_for(status: str, cached: bool) -> str:
    if status == _STATUS_PRO_ACTIVE:
        return CACHED_PRO_MESSAGE if cached else PRO_ACTIVE_MESSAGE
    if status == _STATUS_PRO_EXPIRED:
        return PRO_EXPIRED_MESSAGE
    if status == _STATUS_CHECKING:
        return CHECKING_MESSAGE
    return FREE_MESSAGE


def _format_public_state(record: dict) -> dict:
    """Public view of one stored row. Does not call Lemon or write the database."""
    status = _compute_status(record)
    pro = status == _STATUS_PRO_ACTIVE
    cached = _using_cache(record, status)
    configured = _configured_account_count()
    limit = None if pro else FREE_ACCOUNT_LIMIT
    can_add = pro or configured < FREE_ACCOUNT_LIMIT
    out = {
        "status": status,
        "tier": "pro" if pro else "free",
        "pro": pro,
        "key_present": bool((record.get("license_key") or "").strip()),
        "last_verified_at": record.get("last_verified_at"),
        "cached": cached,
        "account_limit": limit,
        "unlimited_accounts": pro,
        "accounts_configured": configured,
        "can_add_account": can_add,
        "message": _message_for(status, cached),
    }
    if not pro:
        out["limit_message"] = FREE_LIMIT_MESSAGE
        refusal = record.get("lemon_status")
        if refusal in _REFUSAL_MESSAGES and record.get("last_error"):
            out["message"] = record["last_error"]
    # Defence in depth: never leak the stored key even if a future field is added.
    dumped = str(out)
    key = record.get("license_key") or ""
    if key and key in dumped:
        raise RuntimeError("license public_state attempted to expose the license key")
    return out


def public_state(*, refresh: bool = True) -> dict:
    """License state safe to send to the browser / reports / logs.

    Never includes the license key. ``refresh=False`` does not revalidate and
    does not write the stored row.
    """
    record = load_record()
    if refresh:
        record = _refresh_if_due(record)
    return _format_public_state(record)


def _clear_local_license(message: str) -> None:
    now = _now_iso()
    _save_record(
        {
            "license_key": "",
            "valid": 0,
            "lemon_status": None,
            "last_verified_at": now,
            "last_success_at": None,
            "last_error": message,
            "updated_at": now,
            "instance_id": "",
        }
    )


def _persist_explicit_refusal(
    record: dict,
    key: str,
    result: dict,
    *,
    keep_instance: Optional[str] = None,
) -> dict:
    """Save a confirmed refusal and drop offline grace.

    `last_success_at` is cleared so a later network failure cannot restore Pro.
    """
    updated = _apply_remote_result(record, key, result)
    updated["valid"] = 0
    updated["last_success_at"] = None
    if keep_instance is not None:
        updated["instance_id"] = keep_instance
    _save_record(updated)
    return updated


def activate(license_key: str) -> dict:
    """Activate a key on this PC and persist the result.

    One activation at a time. The same key with the same stored `instance_id`
    is not activated again. A different key, while an instance is stored, is
    refused locally. Network failures do not restore Pro after an explicit refusal.
    """
    key = (license_key or "").strip()
    if not key:
        raise LicenseInvalidError("A license key is required.")

    blocked = False
    with _lock:
        existing = load_record()
        stored_key = (existing.get("license_key") or "").strip()
        stored_instance = (existing.get("instance_id") or "").strip()
        if stored_instance and stored_key != key:
            blocked = True
        elif stored_key == key and stored_instance:
            result = _keep_instance(
                validate_with_lemon(key, stored_instance), stored_instance
            )
            if result.get("network_error"):
                raise LicenseNetworkError(NETWORK_ACTIVATE_MESSAGE)
            # The saved instance is gone. Persist that before registering again,
            # so a network failure on the retry cannot keep the old grace.
            if result.get("refusal") == _REFUSAL_UNKNOWN_INSTANCE:
                existing = _persist_explicit_refusal(existing, key, result)
                result = activate_with_lemon(key)
                if result.get("network_error"):
                    raise LicenseNetworkError(NETWORK_ACTIVATE_MESSAGE)
            result = _reject_foreign_activation(key, result)
            record = _apply_remote_result(existing, key, result)
            if not result.get("valid"):
                record["valid"] = 0
                record["last_success_at"] = None
            _save_record(record)
        else:
            result = activate_with_lemon(key)
            if result.get("network_error"):
                raise LicenseNetworkError(NETWORK_ACTIVATE_MESSAGE)
            result = _reject_foreign_activation(key, result)
            record = _apply_remote_result(existing, key, result)
            if not result.get("valid"):
                record["valid"] = 0
                record["last_success_at"] = None
            _save_record(record)

    state = _format_public_state(existing) if blocked else public_state()
    if blocked:
        state["activated"] = False
        state["message"] = DIFFERENT_KEY_MESSAGE
        return state
    state["activated"] = bool(result.get("valid"))
    if result.get("valid"):
        state["message"] = PRO_ACTIVE_MESSAGE
    elif result.get("lemon_status") == "expired":
        state["message"] = PRO_EXPIRED_MESSAGE
    else:
        state["message"] = result.get("error") or INVALID_KEY_MESSAGE
    return state


def deactivate() -> dict:
    """Deactivate this PC and return the installation to Free.

    Success, and an explicit disabled, expired, or unknown-instance refusal,
    clear the key, the instance, and Pro. A network failure changes nothing.
    Account data is untouched.
    """
    with _lock:
        record = load_record()
        key = (record.get("license_key") or "").strip()
        instance_id = (record.get("instance_id") or "").strip()
        failed_message = ""
        if not key and not instance_id:
            outcome = "already_free"
        elif not instance_id:
            _clear_local_license(DEACTIVATED_MESSAGE)
            outcome = "cleared"
        else:
            result = deactivate_with_lemon(key, instance_id)
            if result.get("network_error"):
                raise LicenseNetworkError(NETWORK_ACTIVATE_MESSAGE)
            explicit = result.get("refusal") in (
                _REFUSAL_DISABLED, _REFUSAL_EXPIRED, _REFUSAL_UNKNOWN_INSTANCE,
            )
            if result.get("deactivated"):
                _clear_local_license(DEACTIVATED_MESSAGE)
                outcome = "cleared"
            elif explicit:
                _clear_local_license(result.get("error") or DEACTIVATED_MESSAGE)
                outcome = "refused"
                failed_message = result.get("error") or DEACTIVATED_MESSAGE
            else:
                outcome = "failed"
                failed_message = result.get("error") or INVALID_KEY_MESSAGE

    state = public_state()
    if outcome == "failed":
        state["deactivated"] = False
        state["message"] = failed_message
        return state
    if outcome == "refused":
        state["deactivated"] = False
        state["message"] = failed_message
        return state
    state["deactivated"] = True
    state["message"] = FREE_MESSAGE if outcome == "already_free" else DEACTIVATED_MESSAGE
    return state


def apply_account_cap(endpoints: list) -> list:
    """Return the prefix of `endpoints` allowed by the current license.

    Used by the multi-bridge client. Logs a warning (no secrets) when
    extra URLs are ignored on Free.
    """
    if len(endpoints) <= FREE_ACCOUNT_LIMIT:
        return endpoints
    try:
        allowed = max_accounts()
    except Exception as exc:  # noqa: BLE001
        _log_warning("License check failed (%s); limiting to 1 MT5 account", type(exc).__name__)
        return endpoints[:FREE_ACCOUNT_LIMIT]
    if allowed is None:
        return endpoints
    if len(endpoints) > allowed:
        _log_warning(
            "Free license allows %s MT5 account(s); %s bridge URL(s) are configured. "
            "Additional accounts are ignored until a Pro license is activated in Settings.",
            allowed,
            len(endpoints),
        )
        return endpoints[:allowed]
    return endpoints

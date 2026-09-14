"""Lemon Squeezy license keys — Free (1 MT5 account) vs Pro (unlimited).

Uses the public License API (no Lemon Squeezy secret required):

    POST https://api.lemonsqueezy.com/v1/licenses/validate

Persistence lives in the same SQLite file as the rest of Atlas (`atlas.db`),
in a new `atlas_license` table created with `CREATE TABLE IF NOT EXISTS`.
Existing tables are never dropped or altered.

The license key is stored locally so it can be revalidated, but it is never
returned by the API, written to reports, or included in log messages — the
same scrub discipline used for MT5 passwords and bridge tokens.

Revalidation is at most once per day. If the remote call fails (no network,
timeouts, 5xx), the last successful *valid* check is honoured for 7 days so
a paid customer is not locked out by a brief outage.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import httpx

logger = logging.getLogger("atlas.license")

LEMON_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
FREE_ACCOUNT_LIMIT = 1
REVALIDATE_AFTER = timedelta(days=1)
GRACE_AFTER_VALID = timedelta(days=7)
HTTP_TIMEOUT_SEC = 8.0

# Singleton row id — one license per installation.
_ROW_ID = 1

_STATUS_FREE = "free"
_STATUS_PRO_ACTIVE = "pro_active"
_STATUS_PRO_EXPIRED = "pro_expired"
_STATUS_CHECKING = "checking"

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
FREE_MESSAGE = "Free version: 1 MT5 account."
CHECKING_MESSAGE = "Checking license status…"
CACHED_PRO_MESSAGE = (
    "Pro license active (using the last successful check — the license server "
    "could not be reached just now)."
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS atlas_license (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    license_key TEXT NOT NULL DEFAULT '',
    valid INTEGER NOT NULL DEFAULT 0,
    lemon_status TEXT,
    last_verified_at TEXT,
    last_success_at TEXT,
    last_error TEXT,
    updated_at TEXT
);
"""

_lock = threading.Lock()

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


def _empty_row() -> dict:
    return {
        "license_key": "",
        "valid": 0,
        "lemon_status": None,
        "last_verified_at": None,
        "last_success_at": None,
        "last_error": None,
        "updated_at": None,
    }


def _row_to_dict(row: sqlite3.Row | None) -> dict:
    if row is None:
        return _empty_row()
    return {
        "license_key": row["license_key"] or "",
        "valid": int(row["valid"] or 0),
        "lemon_status": row["lemon_status"],
        "last_verified_at": row["last_verified_at"],
        "last_success_at": row["last_success_at"],
        "last_error": row["last_error"],
        "updated_at": row["updated_at"],
    }


def load_record(path: Optional[Path] = None) -> dict:
    ensure_schema(path)
    with _cx(path) as cx:
        row = cx.execute(
            "SELECT license_key, valid, lemon_status, last_verified_at, "
            "last_success_at, last_error, updated_at FROM atlas_license WHERE id=?",
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
            " last_success_at, last_error, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            " license_key=excluded.license_key,"
            " valid=excluded.valid,"
            " lemon_status=excluded.lemon_status,"
            " last_verified_at=excluded.last_verified_at,"
            " last_success_at=excluded.last_success_at,"
            " last_error=excluded.last_error,"
            " updated_at=excluded.updated_at",
            (
                _ROW_ID,
                key,
                1 if record.get("valid") else 0,
                record.get("lemon_status"),
                record.get("last_verified_at"),
                record.get("last_success_at"),
                scrub(record.get("last_error"), extra_secrets=[key]),
                record.get("updated_at") or _now_iso(),
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


def validate_with_lemon(license_key: str) -> dict:
    """Call Lemon Squeezy validate. Never logs or returns the raw key.

    Result keys:
      network_error: bool
      valid: bool
      lemon_status: str | None  (active / inactive / expired / disabled / invalid)
      error: str | None         (already scrubbed)
    """
    key = (license_key or "").strip()
    if not key:
        return {
            "network_error": False,
            "valid": False,
            "lemon_status": "invalid",
            "error": "A license key is required.",
        }
    try:
        response = httpx.post(
            LEMON_VALIDATE_URL,
            data={"license_key": key},
            headers={"Accept": "application/json"},
            timeout=HTTP_TIMEOUT_SEC,
        )
    except httpx.RequestError as exc:
        _log_warning("Lemon Squeezy validate failed (%s)", type(exc).__name__)
        return {
            "network_error": True,
            "valid": False,
            "lemon_status": None,
            "error": NETWORK_ACTIVATE_MESSAGE,
        }

    if response.status_code >= 500:
        _log_warning("Lemon Squeezy validate returned HTTP %s", response.status_code)
        return {
            "network_error": True,
            "valid": False,
            "lemon_status": None,
            "error": NETWORK_ACTIVATE_MESSAGE,
        }

    try:
        payload = response.json()
    except ValueError:
        _log_warning("Lemon Squeezy validate returned non-JSON (HTTP %s)", response.status_code)
        return {
            "network_error": True,
            "valid": False,
            "lemon_status": None,
            "error": NETWORK_ACTIVATE_MESSAGE,
        }

    if not isinstance(payload, dict):
        return {
            "network_error": False,
            "valid": False,
            "lemon_status": "invalid",
            "error": INVALID_KEY_MESSAGE,
        }

    info = payload.get("license_key") if isinstance(payload.get("license_key"), dict) else {}
    lemon_status = info.get("status") if info else None
    valid = bool(payload.get("valid"))
    if lemon_status in ("expired", "disabled"):
        valid = False
    if not valid and not lemon_status:
        lemon_status = "invalid"

    raw_error = payload.get("error")
    error = scrub(raw_error, extra_secrets=[key]) if raw_error else None
    if not valid and not error:
        error = INVALID_KEY_MESSAGE if lemon_status != "expired" else PRO_EXPIRED_MESSAGE

    return {
        "network_error": False,
        "valid": valid,
        "lemon_status": lemon_status,
        "error": error,
    }


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
        # Keep previous valid / last_success_at; do not mark invalid.
        return record
    record["valid"] = 1 if result.get("valid") else 0
    record["lemon_status"] = result.get("lemon_status")
    if result.get("valid"):
        record["last_success_at"] = now
    return record


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
        result = validate_with_lemon(key)
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

    # Confirmed expired/disabled by a successful API response: not Pro,
    # even if a previous success still falls inside the 7-day window.
    if not is_valid and lemon_status in ("expired", "disabled") and last_verified is not None:
        return _STATUS_PRO_EXPIRED if lemon_status == "expired" else _STATUS_FREE
    if not is_valid and lemon_status == "invalid" and last_verified is not None:
        return _STATUS_FREE
    if is_valid and success_in_grace:
        return _STATUS_PRO_ACTIVE
    if is_valid and not success_in_grace:
        # Previously valid, but the 7-day offline cache has elapsed.
        return _STATUS_FREE
    if success_in_grace:
        return _STATUS_PRO_ACTIVE
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


def public_state() -> dict:
    """License state safe to send to the browser / reports / logs.

    Never includes the license key.
    """
    record = _refresh_if_due(load_record())
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
    # Defence in depth: never leak the stored key even if a future field is added.
    dumped = str(out)
    key = record.get("license_key") or ""
    if key and key in dumped:
        raise RuntimeError("license public_state attempted to expose the license key")
    return out


def activate(license_key: str) -> dict:
    """Validate a key with Lemon Squeezy and persist the result.

    Invalid keys leave the installation on Free (the previous Pro key, if
    any, is replaced only when the new key is accepted as valid *or* the
    caller sent a key that the API confirmed as invalid — so a mistyped
    replacement does not silently keep Pro, and an invalid paste does not
    grant Pro).

    Network failures on activate do not change the stored record.
    """
    key = (license_key or "").strip()
    if not key:
        raise LicenseInvalidError("A license key is required.")

    existing = load_record()
    result = validate_with_lemon(key)
    if result.get("network_error"):
        raise LicenseNetworkError(NETWORK_ACTIVATE_MESSAGE)

    if result.get("valid"):
        record = _apply_remote_result(existing, key, result)
        _save_record(record)
        state = public_state()
        state["activated"] = True
        state["message"] = PRO_ACTIVE_MESSAGE
        return state

    # Confirmed invalid / expired: do not grant Pro. Persist the outcome
    # so GET /api/license can show "pro_expired" / free, but never treat
    # a failed paste as success. A previous Pro key is replaced because
    # the operator explicitly submitted a different key.
    record = _apply_remote_result(existing, key, result)
    record["valid"] = 0
    _save_record(record)
    state = public_state()
    state["activated"] = False
    if result.get("lemon_status") == "expired":
        state["message"] = PRO_EXPIRED_MESSAGE
    else:
        state["message"] = INVALID_KEY_MESSAGE
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

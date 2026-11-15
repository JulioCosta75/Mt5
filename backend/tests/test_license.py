"""Isolated tests for Lemon Squeezy Free/Pro licensing.

These tests do not hit the preview URL or a live Lemon Squeezy account.
httpx is mocked; SQLite uses a per-test tempfile.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import license as lic  # noqa: E402
import mt5_config  # noqa: E402
import mt5_client  # noqa: E402

VALID_KEY = "38b1460a-5104-4067-a91d-77b872934d51"
INVALID_KEY = "00000000-0000-0000-0000-000000000000"
INSTANCE_ID = "47596ad9-a811-4ebf-ac8a-03fc7b6d2a17"
T0 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
_UNSET = object()


class _Clock:
    def __init__(self, when: datetime):
        self.when = when

    def __call__(self) -> datetime:
        return self.when


def _lemon_response(
    valid: bool,
    status: str | None = None,
    error: str | None = None,
    key: str = VALID_KEY,
    *,
    instance_id: str | None | object = _UNSET,
    store_id: int = 1,
    product_id: int = 4,
    activated: bool | None = None,
    deactivated: bool = False,
):
    if instance_id is _UNSET:
        instance_id = INSTANCE_ID if valid else None
    body = {
        "valid": valid,
        "activated": valid if activated is None else activated,
        "deactivated": deactivated,
        "error": error,
        "license_key": None if not valid and status is None else {
            "id": 1,
            "status": status or ("active" if valid else "inactive"),
            "key": key,
            "activation_limit": 1,
            "activation_usage": 1,
            "created_at": "2026-01-01T00:00:00.000000Z",
            "expires_at": None,
        },
        "instance": None if not instance_id else {
            "id": instance_id,
            "name": "atlas-test",
            "created_at": "2026-01-01T00:00:00.000000Z",
        },
        "meta": {
            "store_id": store_id,
            "product_id": product_id,
            "product_name": "Atlas Pro",
        },
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    return resp


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db = tmp_path / "atlas.db"
    monkeypatch.setenv("ATLAS_SQLITE_PATH", str(db))
    monkeypatch.setenv("ATLAS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ATLAS_CONFIG_PATH", str(tmp_path / "mt5_config.json"))
    monkeypatch.setenv("ATLAS_STORE", "sqlite")
    monkeypatch.delenv("MT5_BRIDGE_URL", raising=False)
    monkeypatch.delenv("MT5_BRIDGE_URLS", raising=False)
    monkeypatch.delenv("MT5_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("MT5_BRIDGE_TOKENS", raising=False)
    monkeypatch.delenv("LEMON_STORE_ID", raising=False)
    monkeypatch.delenv("LEMON_PRODUCT_ID", raising=False)
    clock = _Clock(T0)
    monkeypatch.setattr(lic, "_now", clock)
    return db, clock


def _assert_no_key(payload, *keys: str) -> None:
    blob = json.dumps(payload) if not isinstance(payload, str) else payload
    for k in keys:
        assert k not in blob, f"license key leaked into output: {k!r}"


# ---------------------------------------------------------------------------
# Schema / migration
# ---------------------------------------------------------------------------
class TestAtlasDbMigration:
    def test_new_table_does_not_destroy_existing(self, isolated_db):
        db, _clock = isolated_db
        cx = sqlite3.connect(str(db))
        cx.executescript(
            """
            CREATE TABLE mt5_cache (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
            CREATE TABLE mt5_overrides (
                login INTEGER PRIMARY KEY,
                kill_switch INTEGER NOT NULL DEFAULT 0,
                risk_limits TEXT NOT NULL,
                daily_pnl_anchor TEXT
            );
            CREATE TABLE mt5_ea_labels (
                login INTEGER NOT NULL,
                magic INTEGER NOT NULL,
                label TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (login, magic)
            );
            CREATE TABLE atlas_reports (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT,
                source TEXT,
                payload TEXT NOT NULL
            );
            CREATE TABLE atlas_alerts (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                rule_key TEXT NOT NULL,
                state TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at TEXT,
                payload TEXT NOT NULL
            );
            """
        )
        cx.execute(
            "INSERT INTO mt5_cache (id, payload, fetched_at) VALUES (?,?,?)",
            ("account:5609382", '{"login": 5609382}', "2026-01-01T00:00:00+00:00"),
        )
        cx.execute(
            "INSERT INTO mt5_overrides (login, kill_switch, risk_limits, daily_pnl_anchor) "
            "VALUES (?,?,?,?)",
            (5609382, 1, '{"max_daily_loss_pct": 3.0}', None),
        )
        cx.execute(
            "INSERT INTO mt5_ea_labels (login, magic, label, updated_at) VALUES (?,?,?,?)",
            (5609382, 123, "Trend Follow", "2026-01-01T00:00:00+00:00"),
        )
        cx.execute(
            "INSERT INTO atlas_reports (id, account_id, created_at, status, source, payload) "
            "VALUES (?,?,?,?,?,?)",
            ("rep-1", "MT5-5609382", "2026-01-01T00:00:00+00:00", "OK", "auto", "{}"),
        )
        cx.execute(
            "INSERT INTO atlas_alerts "
            "(id, account_id, rule_key, state, severity, message, created_at, updated_at, payload) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("alt-1", "MT5-5609382", "drawdown", "open", "WARNING", "dd",
             "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", "{}"),
        )
        cx.commit()
        cx.close()

        lic.ensure_schema()
        state = lic.public_state()
        assert state["status"] == "free"
        assert state["pro"] is False

        cx = sqlite3.connect(str(db))
        tables = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "atlas_license" in tables
        for existing in (
            "mt5_cache", "mt5_overrides", "mt5_ea_labels",
            "atlas_reports", "atlas_alerts",
        ):
            assert existing in tables
        cache_row = cx.execute("SELECT payload FROM mt5_cache WHERE id=?", ("account:5609382",)).fetchone()
        assert cache_row is not None
        assert "5609382" in cache_row[0]
        ov = cx.execute("SELECT kill_switch FROM mt5_overrides WHERE login=5609382").fetchone()
        assert ov[0] == 1
        assert cx.execute("SELECT label FROM mt5_ea_labels WHERE login=5609382").fetchone()[0] == "Trend Follow"
        assert cx.execute("SELECT id FROM atlas_reports WHERE id='rep-1'").fetchone()[0] == "rep-1"
        assert cx.execute("SELECT id FROM atlas_alerts WHERE id='alt-1'").fetchone()[0] == "alt-1"
        cx.close()


# ---------------------------------------------------------------------------
# License states
# ---------------------------------------------------------------------------
class TestLicenseStates:
    def test_free_without_key(self, isolated_db):
        state = lic.public_state()
        assert state["status"] == "free"
        assert state["tier"] == "free"
        assert state["pro"] is False
        assert state["key_present"] is False
        assert state["account_limit"] == 1
        assert state["unlimited_accounts"] is False
        assert state["can_add_account"] is True
        assert "license_key" not in state
        _assert_no_key(state, VALID_KEY, INVALID_KEY)

    def test_valid_key_activates_pro(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        state = lic.activate(VALID_KEY)
        assert state["activated"] is True
        assert state["status"] == "pro_active"
        assert state["pro"] is True
        assert state["unlimited_accounts"] is True
        assert state["account_limit"] is None
        assert state["can_add_account"] is True
        _assert_no_key(state, VALID_KEY)
        assert lic.is_pro_active() is True
        lic.enforce_account_limit(99)  # unlimited — must not raise

    def test_invalid_key_stays_free(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(
                False, status=None, error=f"license_key {INVALID_KEY} not found", key=INVALID_KEY,
            ),
        )
        state = lic.activate(INVALID_KEY)
        assert state["activated"] is False
        assert state["status"] == "free"
        assert state["pro"] is False
        assert state["account_limit"] == 1
        assert "not valid" in state["message"].lower() or "could not be validated" in state["message"].lower()
        _assert_no_key(state, INVALID_KEY)
        assert lic.is_pro_active() is False
        with pytest.raises(lic.AccountLimitError, match="1 MT5 account"):
            lic.enforce_account_limit(2)

    def test_expired_key_is_not_pro(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(False, status="expired", error="expired", key=VALID_KEY),
        )
        state = lic.activate(VALID_KEY)
        assert state["activated"] is False
        assert state["pro"] is False
        assert state["status"] == "pro_expired"
        _assert_no_key(state, VALID_KEY)

    def test_network_failure_keeps_cached_pro(self, isolated_db, monkeypatch):
        db, clock = isolated_db
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        lic.activate(VALID_KEY)
        assert lic.is_pro_active() is True

        def boom(*a, **k):
            req = httpx.Request("POST", lic.LEMON_VALIDATE_URL)
            raise httpx.ConnectError("No route to host", request=req)

        monkeypatch.setattr(lic.httpx, "post", boom)
        clock.when = T0 + timedelta(days=2)
        assert lic.is_pro_active() is True
        state = lic.public_state()
        assert state["status"] == "pro_active"
        assert state["cached"] is True
        assert state["pro"] is True
        lic.enforce_account_limit(5)

    def test_grace_expired_without_revalidation_returns_free(self, isolated_db, monkeypatch):
        db, clock = isolated_db
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        lic.activate(VALID_KEY)

        def boom(*a, **k):
            req = httpx.Request("POST", lic.LEMON_VALIDATE_URL)
            raise httpx.ConnectError("No route to host", request=req)

        monkeypatch.setattr(lic.httpx, "post", boom)
        clock.when = T0 + timedelta(days=8)
        assert lic.is_pro_active() is False
        state = lic.public_state()
        assert state["status"] == "free"
        assert state["pro"] is False
        assert state["account_limit"] == 1
        with pytest.raises(lic.AccountLimitError):
            lic.enforce_account_limit(2)

    def test_revalidate_at_most_once_per_day(self, isolated_db, monkeypatch):
        calls = {"n": 0}

        def counting(*a, **k):
            calls["n"] += 1
            return _lemon_response(True, status="active", key=VALID_KEY)

        monkeypatch.setattr(lic.httpx, "post", counting)
        lic.activate(VALID_KEY)
        assert calls["n"] == 1
        lic.public_state()
        lic.is_pro_active()
        lic.public_state()
        assert calls["n"] == 1  # still within the same day

    def test_http_5xx_is_network_not_invalid(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        lic.activate(VALID_KEY)

        def fivehundred(*a, **k):
            resp = MagicMock()
            resp.status_code = 503
            resp.json.return_value = {"error": f"license_key={VALID_KEY} boom"}
            return resp

        monkeypatch.setattr(lic.httpx, "post", fivehundred)
        clock = isolated_db[1]
        clock.when = T0 + timedelta(days=2)
        assert lic.is_pro_active() is True

    def test_activate_network_error_does_not_grant_pro(self, isolated_db, monkeypatch):
        def boom(*a, **k):
            req = httpx.Request("POST", lic.LEMON_VALIDATE_URL)
            raise httpx.ConnectError("offline", request=req)

        monkeypatch.setattr(lic.httpx, "post", boom)
        with pytest.raises(lic.LicenseNetworkError):
            lic.activate(VALID_KEY)
        assert lic.is_pro_active() is False
        assert lic.public_state()["status"] == "free"


# ---------------------------------------------------------------------------
# Scrub / no leak
# ---------------------------------------------------------------------------
class TestScrub:
    def test_scrub_redacts_assignment_and_explicit_secret(self):
        raw = f"license_key={VALID_KEY} extra"
        out = lic.scrub(raw, extra_secrets=[VALID_KEY])
        assert VALID_KEY not in out
        assert "[redacted]" in out

    def test_stored_error_does_not_contain_key(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(
                False, error=f"license_key {INVALID_KEY} not found", key=INVALID_KEY,
            ),
        )
        lic.activate(INVALID_KEY)
        record = lic.load_record()
        assert INVALID_KEY not in (record.get("last_error") or "")
        dumped = json.dumps(dict(record))
        # The key is stored in license_key (local sqlite) but last_error must be clean.
        assert INVALID_KEY not in (record.get("last_error") or "")
        _assert_no_key({"error": record.get("last_error")}, INVALID_KEY)


# ---------------------------------------------------------------------------
# Account limit
# ---------------------------------------------------------------------------
class TestAccountLimit:
    def test_free_allows_first_account_save(self, isolated_db):
        cfg = mt5_config.save_config({
            "login": "12345678",
            "password": "secret123",
            "server": "Darwinex-Live",
            "bridge_port": 8002,
        })
        assert cfg["configured"] is True
        assert cfg["login"] == "12345678"
        # Replacing the same slot (switch broker) stays allowed on Free.
        cfg2 = mt5_config.save_config({
            "login": "87654321",
            "password": "secret123",
            "server": "ICMarkets-Live01",
            "bridge_port": 8002,
        })
        assert cfg2["login"] == "87654321"
        masked = mt5_config.masked(cfg2)
        assert "password" not in masked
        assert masked["password_set"] is True

    def test_free_blocks_second_simultaneous_account(self, isolated_db):
        mt5_config.save_config({
            "login": "12345678",
            "password": "secret123",
            "server": "Darwinex-Live",
        })
        with pytest.raises(lic.AccountLimitError, match="Settings"):
            mt5_config.assert_can_add_account()
        with pytest.raises(mt5_config.ConfigError):
            # validation still works independently of licensing
            mt5_config.save_config({"login": "abc", "password": "x", "server": "S"})

    def test_pro_allows_unlimited_accounts(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        lic.activate(VALID_KEY)
        mt5_config.save_config({
            "login": "12345678",
            "password": "secret123",
            "server": "Darwinex-Live",
        })
        mt5_config.assert_can_add_account()  # must not raise
        urls = mt5_config.licensed_bridge_urls(
            ["http://a:1", "http://b:2", "http://c:3"]
        )
        assert urls == ["http://a:1", "http://b:2", "http://c:3"]

    def test_clients_capped_on_free(self, isolated_db, monkeypatch):
        monkeypatch.setenv("MT5_BRIDGE_URLS", "http://a:1,http://b:2,http://c:3")
        monkeypatch.setenv("MT5_BRIDGE_TOKENS", "t1,t2,t3")
        raw = mt5_client.configured_bridges()
        assert len(raw) == 3
        capped = mt5_client.clients()
        assert len(capped) == 1
        assert capped[0].endpoint.url == "http://a:1"

    def test_clients_unlimited_on_pro(self, isolated_db, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        lic.activate(VALID_KEY)
        monkeypatch.setenv("MT5_BRIDGE_URLS", "http://a:1,http://b:2,http://c:3")
        monkeypatch.setenv("MT5_BRIDGE_TOKENS", "t1,t2,t3")
        clients = mt5_client.clients()
        assert len(clients) == 3
        assert [c.endpoint.url for c in clients] == ["http://a:1", "http://b:2", "http://c:3"]


# ---------------------------------------------------------------------------
# HTTP endpoints (in-process, no preview URL)
# ---------------------------------------------------------------------------
class TestLicenseEndpoints:
    @pytest.fixture
    def client(self, isolated_db, monkeypatch):
        from fastapi.testclient import TestClient
        import server

        return TestClient(server.app)

    def test_get_license_free_default(self, client):
        r = client.get("/api/license")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "free"
        assert d["pro"] is False
        assert "license_key" not in d
        _assert_no_key(d, VALID_KEY, INVALID_KEY)

    def test_activate_valid(self, client, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", key=VALID_KEY),
        )
        r = client.post("/api/license/activate", json={"license_key": VALID_KEY})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["activated"] is True
        assert d["status"] == "pro_active"
        assert VALID_KEY not in r.text
        g = client.get("/api/license")
        assert g.json()["pro"] is True
        assert VALID_KEY not in g.text

    def test_activate_invalid(self, client, monkeypatch):
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(False, error="not found", key=INVALID_KEY),
        )
        r = client.post("/api/license/activate", json={"license_key": INVALID_KEY})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["activated"] is False
        assert d["status"] == "free"
        assert INVALID_KEY not in r.text

    def test_activate_empty_key(self, client):
        r = client.post("/api/license/activate", json={"license_key": "  "})
        assert r.status_code == 422

    def test_activate_network_error(self, client, monkeypatch):
        def boom(*a, **k):
            req = httpx.Request("POST", lic.LEMON_VALIDATE_URL)
            raise httpx.ConnectError("offline", request=req)

        monkeypatch.setattr(lic.httpx, "post", boom)
        r = client.post("/api/license/activate", json={"license_key": VALID_KEY})
        assert r.status_code == 503
        assert VALID_KEY not in r.text
        assert client.get("/api/license").json()["pro"] is False

    def test_mt5_config_first_account_still_works(self, client):
        r = client.put("/api/mt5/config", json={
            "login": "12345678",
            "password": "secret123",
            "server": "Darwinex-Live",
            "bridge_port": 8002,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["saved"] is True
        assert "password" not in d["config"]
        assert "secret123" not in r.text
        g = client.get("/api/mt5/config")
        assert g.json()["config"]["login"] == "12345678"
        # Free + 1 configured account: license endpoint reports the slot in use.
        lic_state = client.get("/api/license").json()
        assert lic_state["pro"] is False
        assert lic_state["accounts_configured"] >= 1
        assert lic_state["can_add_account"] is False


# ---------------------------------------------------------------------------
# Per-PC activation, store/product check, deactivate
# ---------------------------------------------------------------------------
def _capture_post(monkeypatch, responder):
    calls = []

    def post(url, data=None, **kwargs):
        calls.append((url, dict(data or {})))
        return responder(url, dict(data or {}), **kwargs)

    monkeypatch.setattr(lic.httpx, "post", post)
    return calls


def _ok_or_deactivate(url, data, **kwargs):
    if url == lic.LEMON_DEACTIVATE_URL:
        return _lemon_response(False, status="inactive", deactivated=True, instance_id=None)
    return _lemon_response(True, status="active")


class TestPerPcActivation:
    def test_instance_name_is_a_stable_hash_without_the_raw_material(self, monkeypatch):
        monkeypatch.setattr(lic, "_machine_material", lambda: "SECRET-GUID")
        name = lic.machine_instance_name()
        assert name.startswith("atlas-")
        assert "SECRET-GUID" not in name
        digest = name.removeprefix("atlas-")
        assert len(digest) == 32
        assert digest == hashlib.sha256(b"SECRET-GUID").hexdigest()[:32]
        assert lic.machine_instance_name() == name

    def test_activate_posts_instance_name_and_stores_instance_id(self, isolated_db, monkeypatch):
        calls = _capture_post(monkeypatch, lambda url, data, **k: _lemon_response(True, status="active"))
        state = lic.activate(VALID_KEY)
        assert state["activated"] is True
        assert state["pro"] is True
        assert calls[0][0] == lic.LEMON_ACTIVATE_URL
        assert calls[0][1]["license_key"] == VALID_KEY
        assert calls[0][1]["instance_name"].startswith("atlas-")
        assert "instance_id" not in calls[0][1]
        assert VALID_KEY not in calls[0][1]["instance_name"]
        record = lic.load_record()
        assert record["instance_id"] == INSTANCE_ID
        assert record["license_key"] == VALID_KEY
        _assert_no_key(state, VALID_KEY)

    def test_same_pc_does_not_activate_again(self, isolated_db, monkeypatch):
        calls = _capture_post(monkeypatch, lambda url, data, **k: _lemon_response(True, status="active"))
        lic.activate(VALID_KEY)
        again = lic.activate(VALID_KEY)
        assert again["activated"] is True
        assert again["pro"] is True
        assert [url for url, _data in calls] == [lic.LEMON_ACTIVATE_URL, lic.LEMON_VALIDATE_URL]
        assert calls[1][1]["instance_id"] == INSTANCE_ID
        assert calls[1][1]["license_key"] == VALID_KEY
        assert "instance_name" not in calls[1][1]

    def test_revalidate_sends_instance_id(self, isolated_db, monkeypatch):
        db, clock = isolated_db
        calls = _capture_post(monkeypatch, lambda url, data, **k: _lemon_response(True, status="active"))
        lic.activate(VALID_KEY)
        clock.when = T0 + timedelta(days=2)
        assert lic.is_pro_active() is True
        assert calls[1][0] == lic.LEMON_VALIDATE_URL
        assert calls[1][1]["license_key"] == VALID_KEY
        assert calls[1][1]["instance_id"] == INSTANCE_ID
        state = lic.public_state()
        _assert_no_key(state, VALID_KEY)

    def test_activation_limit_stays_free_and_keeps_account_data(self, isolated_db, monkeypatch, caplog):
        db, _clock = isolated_db
        cx = sqlite3.connect(str(db))
        cx.execute(
            "CREATE TABLE mt5_overrides (login INTEGER PRIMARY KEY, kill_switch INTEGER NOT NULL)"
        )
        cx.execute("INSERT INTO mt5_overrides (login, kill_switch) VALUES (5609382, 1)")
        cx.commit()
        cx.close()

        def post(url, data, **kwargs):
            return _lemon_response(
                False,
                status="active",
                error=f"This license key has reached the activation limit. license_key={VALID_KEY}",
                instance_id=None,
            )

        calls = _capture_post(monkeypatch, post)
        with caplog.at_level(logging.WARNING, logger="atlas.license"):
            state = lic.activate(VALID_KEY)
        assert state["activated"] is False
        assert state["pro"] is False
        assert state["status"] == "free"
        assert state["message"] == (
            "This key is already active on another PC. Deactivate it there or contact support."
        )
        assert calls[0][0] == lic.LEMON_ACTIVATE_URL
        _assert_no_key(state, VALID_KEY)
        assert VALID_KEY not in caplog.text
        record = lic.load_record()
        assert record["valid"] == 0
        assert record["lemon_status"] == "activation_limit"
        assert VALID_KEY not in (record.get("last_error") or "")
        cx = sqlite3.connect(str(db))
        assert cx.execute("SELECT kill_switch FROM mt5_overrides WHERE login=5609382").fetchone()[0] == 1
        cx.close()

    def test_limit_refusal_is_not_retried_as_validate_without_instance(self, isolated_db, monkeypatch):
        _db, clock = isolated_db
        calls = _capture_post(
            monkeypatch,
            lambda url, data, **k: _lemon_response(
                False,
                status="active",
                error="This license key has reached the activation limit.",
                instance_id=None,
            ),
        )
        lic.activate(VALID_KEY)
        clock.when = T0 + timedelta(days=2)
        state = lic.public_state()
        assert state["pro"] is False
        assert state["status"] == "free"
        assert [url for url, _data in calls] == [lic.LEMON_ACTIVATE_URL]

    def test_wrong_store_and_product_do_not_grant_pro(self, isolated_db, monkeypatch):
        monkeypatch.setenv("LEMON_STORE_ID", "10")
        monkeypatch.setenv("LEMON_PRODUCT_ID", "20")
        calls = _capture_post(
            monkeypatch,
            lambda url, data, **k: _lemon_response(
                False, status="inactive", deactivated=True, instance_id=None,
            ) if url == lic.LEMON_DEACTIVATE_URL else _lemon_response(
                True, status="active", store_id=99, product_id=20,
            ),
        )
        state = lic.activate(VALID_KEY)
        assert state["activated"] is False
        assert state["pro"] is False
        assert "not from the Sr Atlas store" in state["message"]
        assert calls[0][0] == lic.LEMON_ACTIVATE_URL
        assert calls[1][0] == lic.LEMON_DEACTIVATE_URL
        assert calls[1][1]["instance_id"] == INSTANCE_ID
        assert lic.load_record()["instance_id"] == ""
        assert lic.is_pro_active() is False

        calls.clear()
        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", store_id=10, product_id=77),
        )
        state = lic.activate(VALID_KEY)
        assert state["pro"] is False
        assert "not for Sr Atlas Pro" in state["message"]

        monkeypatch.setattr(
            lic.httpx, "post",
            lambda *a, **k: _lemon_response(True, status="active", store_id=10, product_id=20),
        )
        state = lic.activate(VALID_KEY)
        assert state["activated"] is True
        assert state["pro"] is True

    def test_store_check_skipped_while_ids_are_zero(self, isolated_db, monkeypatch, caplog):
        monkeypatch.setattr(lic, "_store_product_warning_logged", False)
        calls = {"n": 0}

        def post(*args, **kwargs):
            calls["n"] += 1
            return _lemon_response(True, status="active", store_id=999, product_id=888)

        monkeypatch.setattr(lic.httpx, "post", post)
        with caplog.at_level(logging.WARNING, logger="atlas.license"):
            state = lic.activate(VALID_KEY)
            again = lic.activate(VALID_KEY)
        assert state["pro"] is True
        assert again["pro"] is True
        warnings = [r for r in caplog.records if "LEMON_STORE_ID" in r.getMessage()]
        assert len(warnings) == 1
        assert VALID_KEY not in caplog.text

    def test_explicit_refusal_ignores_offline_grace(self, isolated_db, monkeypatch):
        _db, clock = isolated_db

        def post(url, data=None, **kwargs):
            if url == lic.LEMON_VALIDATE_URL:
                return _lemon_response(
                    False,
                    status="disabled",
                    error="This license key is disabled.",
                    instance_id=None,
                )
            return _lemon_response(True, status="active")

        monkeypatch.setattr(lic.httpx, "post", post)
        lic.activate(VALID_KEY)
        assert lic.is_pro_active() is True
        clock.when = T0 + timedelta(days=2)
        assert lic.is_pro_active() is False
        state = lic.public_state()
        assert state["status"] == "free"
        assert state["pro"] is False
        assert state["cached"] is False
        assert "disabled" in state["message"].lower()
        with pytest.raises(lic.AccountLimitError):
            lic.enforce_account_limit(2)

    def test_activate_retries_when_saved_instance_is_unknown(self, isolated_db, monkeypatch):
        calls = _capture_post(
            monkeypatch,
            lambda url, data, **k: _lemon_response(
                False,
                status="active",
                error="This license key instance does not exist.",
                instance_id=None,
            ) if url == lic.LEMON_VALIDATE_URL else _lemon_response(True, status="active"),
        )
        lic.activate(VALID_KEY)
        again = lic.activate(VALID_KEY)
        assert again["activated"] is True
        assert again["pro"] is True
        assert [url for url, _data in calls] == [
            lic.LEMON_ACTIVATE_URL,
            lic.LEMON_VALIDATE_URL,
            lic.LEMON_ACTIVATE_URL,
        ]

    def test_unknown_instance_returns_free_without_a_new_activation(self, isolated_db, monkeypatch):
        _db, clock = isolated_db
        calls = _capture_post(
            monkeypatch,
            lambda url, data, **k: _lemon_response(
                False,
                status="active",
                error="This license key instance does not exist.",
                instance_id=None,
            ) if url == lic.LEMON_VALIDATE_URL else _lemon_response(True, status="active"),
        )
        lic.activate(VALID_KEY)
        clock.when = T0 + timedelta(days=2)
        state = lic.public_state()
        assert state["pro"] is False
        assert "not active on this PC" in state["message"]
        assert [url for url, _data in calls] == [lic.LEMON_ACTIVATE_URL, lic.LEMON_VALIDATE_URL]
        assert lic.load_record()["instance_id"] == ""
        clock.when = T0 + timedelta(days=4)
        lic.public_state()
        assert [url for url, _data in calls] == [lic.LEMON_ACTIVATE_URL, lic.LEMON_VALIDATE_URL]
        again = lic.activate(VALID_KEY)
        assert again["activated"] is True
        assert again["pro"] is True
        assert [url for url, _data in calls] == [
            lic.LEMON_ACTIVATE_URL, lic.LEMON_VALIDATE_URL, lic.LEMON_ACTIVATE_URL,
        ]

    def test_legacy_row_registers_this_pc_on_refresh(self, isolated_db, monkeypatch):
        db, _clock = isolated_db
        old = (T0 - timedelta(days=2)).isoformat()
        lic.ensure_schema()
        cx = sqlite3.connect(str(db))
        cx.execute(
            "INSERT INTO atlas_license "
            "(id, license_key, valid, lemon_status, last_verified_at, last_success_at, "
            " last_error, updated_at, instance_id) "
            "VALUES (1, ?, 1, 'active', ?, ?, '', ?, '')",
            (VALID_KEY, old, old, old),
        )
        cx.commit()
        cx.close()
        calls = _capture_post(monkeypatch, lambda url, data, **k: _lemon_response(True, status="active"))
        assert lic.is_pro_active() is True
        assert calls[0][0] == lic.LEMON_ACTIVATE_URL
        assert calls[0][1]["instance_name"].startswith("atlas-")
        record = lic.load_record()
        assert record["license_key"] == VALID_KEY
        assert record["instance_id"] == INSTANCE_ID
        assert record["valid"] == 1

    def test_migrate_instance_column_keeps_existing_row(self, isolated_db):
        db, _clock = isolated_db
        cx = sqlite3.connect(str(db))
        cx.executescript(
            """
            CREATE TABLE atlas_license (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                license_key TEXT NOT NULL DEFAULT '',
                valid INTEGER NOT NULL DEFAULT 0,
                lemon_status TEXT,
                last_verified_at TEXT,
                last_success_at TEXT,
                last_error TEXT,
                updated_at TEXT
            );
            CREATE TABLE mt5_overrides (
                login INTEGER PRIMARY KEY,
                kill_switch INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        cx.execute(
            "INSERT INTO atlas_license "
            "(id, license_key, valid, lemon_status, last_verified_at, last_success_at, last_error, updated_at) "
            "VALUES (1, ?, 1, 'active', ?, ?, '', ?)",
            (VALID_KEY, T0.isoformat(), T0.isoformat(), T0.isoformat()),
        )
        cx.execute("INSERT INTO mt5_overrides (login, kill_switch) VALUES (5609382, 1)")
        cx.commit()
        cx.close()

        lic.ensure_schema()
        lic.ensure_schema()

        cx = sqlite3.connect(str(db))
        cols = [r[1] for r in cx.execute("PRAGMA table_info(atlas_license)")]
        assert cols.count("instance_id") == 1
        row = cx.execute(
            "SELECT license_key, valid, lemon_status FROM atlas_license WHERE id=1"
        ).fetchone()
        assert row == (VALID_KEY, 1, "active")
        assert cx.execute("SELECT kill_switch FROM mt5_overrides WHERE login=5609382").fetchone()[0] == 1
        cx.close()
        record = lic.load_record()
        assert record["license_key"] == VALID_KEY
        assert record["valid"] == 1
        assert record["instance_id"] == ""

    def test_deactivate_returns_free_and_calls_lemon(self, isolated_db, monkeypatch):
        db, _clock = isolated_db
        cx = sqlite3.connect(str(db))
        cx.execute(
            "CREATE TABLE mt5_overrides (login INTEGER PRIMARY KEY, kill_switch INTEGER NOT NULL)"
        )
        cx.execute("INSERT INTO mt5_overrides (login, kill_switch) VALUES (5609382, 1)")
        cx.commit()
        cx.close()
        calls = _capture_post(monkeypatch, _ok_or_deactivate)
        lic.activate(VALID_KEY)
        assert lic.is_pro_active() is True
        state = lic.deactivate()
        assert state["deactivated"] is True
        assert state["pro"] is False
        assert state["status"] == "free"
        assert state["key_present"] is False
        assert "deactivated on this PC" in state["message"]
        assert calls[-1][0] == lic.LEMON_DEACTIVATE_URL
        assert calls[-1][1]["license_key"] == VALID_KEY
        assert calls[-1][1]["instance_id"] == INSTANCE_ID
        _assert_no_key(state, VALID_KEY)
        record = lic.load_record()
        assert record["license_key"] == ""
        assert record["instance_id"] == ""
        assert record["valid"] == 0
        cx = sqlite3.connect(str(db))
        assert cx.execute("SELECT kill_switch FROM mt5_overrides WHERE login=5609382").fetchone()[0] == 1
        cx.close()

    def test_deactivate_network_error_keeps_pro(self, isolated_db, monkeypatch):
        def post(url, data=None, **kwargs):
            if url == lic.LEMON_DEACTIVATE_URL:
                req = httpx.Request("POST", url)
                raise httpx.ConnectError("offline", request=req)
            return _lemon_response(True, status="active")

        monkeypatch.setattr(lic.httpx, "post", post)
        lic.activate(VALID_KEY)
        with pytest.raises(lic.LicenseNetworkError):
            lic.deactivate()
        assert lic.is_pro_active() is True
        assert lic.load_record()["instance_id"] == INSTANCE_ID

    def test_deactivate_endpoint(self, isolated_db, monkeypatch):
        from fastapi.testclient import TestClient
        import server

        calls = _capture_post(monkeypatch, _ok_or_deactivate)
        client = TestClient(server.app)
        activated = client.post("/api/license/activate", json={"license_key": VALID_KEY})
        assert activated.status_code == 200, activated.text
        assert activated.json()["pro"] is True
        response = client.post("/api/license/deactivate")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["deactivated"] is True
        assert body["pro"] is False
        assert body["status"] == "free"
        assert VALID_KEY not in response.text
        assert calls[-1][0] == lic.LEMON_DEACTIVATE_URL
        follow = client.get("/api/license")
        assert follow.json()["pro"] is False
        assert VALID_KEY not in follow.text

    def test_deactivate_endpoint_network_and_empty(self, isolated_db, monkeypatch):
        from fastapi.testclient import TestClient
        import server

        client = TestClient(server.app)
        empty = client.post("/api/license/deactivate")
        assert empty.status_code == 200, empty.text
        assert empty.json()["pro"] is False
        assert empty.json()["deactivated"] is True

        def post(url, data=None, **kwargs):
            if url == lic.LEMON_DEACTIVATE_URL:
                req = httpx.Request("POST", url)
                raise httpx.ConnectError("offline", request=req)
            return _lemon_response(True, status="active")

        monkeypatch.setattr(lic.httpx, "post", post)
        activated = client.post("/api/license/activate", json={"license_key": VALID_KEY})
        assert activated.status_code == 200, activated.text
        failed = client.post("/api/license/deactivate")
        assert failed.status_code == 503
        assert VALID_KEY not in failed.text
        assert client.get("/api/license").json()["pro"] is True

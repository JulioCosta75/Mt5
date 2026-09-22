"""Isolated tests for Lemon Squeezy Free/Pro licensing.

These tests do not hit the preview URL or a live Lemon Squeezy account.
httpx is mocked; SQLite uses a per-test tempfile.
"""
from __future__ import annotations

import json
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
T0 = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)


class _Clock:
    def __init__(self, when: datetime):
        self.when = when

    def __call__(self) -> datetime:
        return self.when


def _lemon_response(valid: bool, status: str | None = None, error: str | None = None, key: str = VALID_KEY):
    body = {
        "valid": valid,
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
        "instance": None,
        "meta": {"product_name": "Atlas Pro"},
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
        cx.commit()
        cx.close()

        lic.ensure_schema()
        state = lic.public_state()
        assert state["status"] == "free"
        assert state["pro"] is False

        cx = sqlite3.connect(str(db))
        tables = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "atlas_license" in tables
        assert "mt5_cache" in tables
        assert "mt5_overrides" in tables
        cache_row = cx.execute("SELECT payload FROM mt5_cache WHERE id=?", ("account:5609382",)).fetchone()
        assert cache_row is not None
        assert "5609382" in cache_row[0]
        ov = cx.execute("SELECT kill_switch FROM mt5_overrides WHERE login=5609382").fetchone()
        assert ov[0] == 1
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

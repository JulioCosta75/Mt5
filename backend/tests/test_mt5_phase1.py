"""Phase 1 backend tests:
1. Regression in mock mode (against deployed preview URL).
2. MT5 mode activation tests using in-process FastAPI TestClient with a
   bogus MT5_BRIDGE_URL so the bridge is intentionally unreachable.
3. Unit tests for mt5_adapter and mt5_client.

NOTE: These tests must not write MT5_BRIDGE_URL to /app/backend/.env so the
preview stays in mock mode for the user.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://windows-setup-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Make /app/backend importable for the in-process tests
BACKEND_DIR = Path("/app/backend").resolve()
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# 1) Regression — mock-mode behaviour against the deployed preview URL
# ---------------------------------------------------------------------------
class TestMockRegression:
    """Verifies the existing public API still works in mock mode."""

    def test_kpis_mock(self):
        r = requests.get(f"{API}/kpis", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["accounts_total"] == 8
        # mock mode must NOT advertise a 'mt5' source
        assert d.get("source", "mock") != "mt5"

    def test_accounts_mock(self):
        r = requests.get(f"{API}/accounts", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) == 8
        assert items[0]["id"] == "ACC-001"

    def test_account_detail_endpoints(self):
        r1 = requests.get(f"{API}/accounts/ACC-001/equity?points=50", timeout=15)
        r2 = requests.get(f"{API}/accounts/ACC-001/drawdown?points=50", timeout=15)
        r3 = requests.get(f"{API}/accounts/ACC-001/trades?limit=10", timeout=15)
        for r in (r1, r2, r3):
            assert r.status_code == 200, r.text
        assert r1.json()["account_id"] == "ACC-001"
        assert r2.json()["account_id"] == "ACC-001"
        assert len(r3.json()["trades"]) <= 10

    def test_kill_switch_toggle_mock(self):
        # toggle ON
        on = requests.post(f"{API}/accounts/ACC-001/kill-switch",
                           json={"enabled": True}, timeout=15)
        assert on.status_code == 200
        assert on.json()["status"] == "PAUSED"

        # restore
        off = requests.post(f"{API}/accounts/ACC-001/kill-switch",
                            json={"enabled": False}, timeout=15)
        assert off.status_code == 200
        assert off.json()["status"] == "LIVE"


# ---------------------------------------------------------------------------
# 2) Adapter unit tests
# ---------------------------------------------------------------------------
class TestAdapter:
    def test_drawdown_from_equity_basic(self):
        from mt5_adapter import drawdown_from_equity
        series = [
            {"t": "2026-01-01T00:00:00", "equity": 100},
            {"t": "2026-01-02T00:00:00", "equity": 120},
            {"t": "2026-01-03T00:00:00", "equity": 90},
        ]
        dd_series, max_dd, current_dd = drawdown_from_equity(series)
        assert len(dd_series) == 3
        # peak after point 2 is 120, then drop to 90 → -25%
        assert dd_series[0]["dd"] == 0.0
        assert dd_series[1]["dd"] == 0.0
        assert dd_series[2]["dd"] == pytest.approx(-25.0, abs=0.01)
        assert max_dd == pytest.approx(-25.0, abs=0.01)
        assert current_dd == pytest.approx(-25.0, abs=0.01)

    def test_drawdown_empty(self):
        from mt5_adapter import drawdown_from_equity
        assert drawdown_from_equity([]) == ([], 0.0, 0.0)

    def test_account_from_bridge_mapping(self):
        from mt5_adapter import account_from_bridge
        bridge = {
            "login": 5609382,
            "name": "Test",
            "broker": "ICMarkets-Live01",
            "currency": "USD",
            "leverage": 200,
            "balance": 100000.0,
            "equity": 101234.56,
            "margin": 5000.0,
            "margin_free": 96234.56,
            "profit": 1234.56,
            "connected": True,
            "trade_allowed": True,
            "server": "ICMarkets-Live01",
        }
        acc = account_from_bridge(
            bridge, positions_count=4,
            risk_limits={"max_daily_loss_pct": 3.0},
            kill_switch=False, max_dd=-5.0, current_dd=-1.2,
            daily_pnl_anchor=None,
        )
        assert acc["id"] == "MT5-5609382"
        assert acc["login"] == 5609382
        assert acc["broker"] == "ICMarkets-Live01"
        assert acc["balance"] == 100000.0
        assert acc["equity"] == 101234.56
        assert acc["margin_used"] == 5000.0
        # margin level = 101234.56 / 5000 * 100
        assert acc["margin_level"] == pytest.approx(2024.7, abs=0.5)
        assert acc["open_positions"] == 4
        assert acc["status"] == "LIVE"
        assert acc["source"] == "mt5"
        # kill_switch propagation
        acc2 = account_from_bridge(bridge, 0, {}, kill_switch=True)
        assert acc2["status"] == "PAUSED"
        # disconnected
        bridge2 = {**bridge, "connected": False}
        acc3 = account_from_bridge(bridge2, 0, {}, kill_switch=False)
        assert acc3["status"] == "ERROR"
        # daily_pnl from anchor (equity - anchor)
        acc4 = account_from_bridge(bridge, 0, {}, kill_switch=False,
                                   daily_pnl_anchor=100000.0)
        assert acc4["daily_pnl"] == pytest.approx(1234.56, abs=0.01)


# ---------------------------------------------------------------------------
# 3) mt5_client.configured_bridges env handling
# ---------------------------------------------------------------------------
class TestBridgeConfig:
    def _reload(self):
        if "mt5_client" in sys.modules:
            return importlib.reload(sys.modules["mt5_client"])
        import mt5_client  # noqa
        return sys.modules["mt5_client"]

    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("MT5_BRIDGE_URL", raising=False)
        monkeypatch.delenv("MT5_BRIDGE_URLS", raising=False)
        monkeypatch.delenv("MT5_BRIDGE_TOKEN", raising=False)
        monkeypatch.delenv("MT5_BRIDGE_TOKENS", raising=False)
        mod = self._reload()
        assert mod.configured_bridges() == []

    def test_single_url(self, monkeypatch):
        monkeypatch.delenv("MT5_BRIDGE_URLS", raising=False)
        monkeypatch.setenv("MT5_BRIDGE_URL", "http://127.0.0.1:9999")
        monkeypatch.setenv("MT5_BRIDGE_TOKEN", "abc")
        mod = self._reload()
        bridges = mod.configured_bridges()
        assert len(bridges) == 1
        assert bridges[0].url == "http://127.0.0.1:9999"
        assert bridges[0].token == "abc"

    def test_multi_urls(self, monkeypatch):
        monkeypatch.delenv("MT5_BRIDGE_URL", raising=False)
        monkeypatch.setenv("MT5_BRIDGE_URLS", "http://a:1,http://b:2,http://c:3")
        monkeypatch.setenv("MT5_BRIDGE_TOKENS", "t1,t2,t3")
        mod = self._reload()
        bridges = mod.configured_bridges()
        assert len(bridges) == 3
        assert [b.url for b in bridges] == ["http://a:1", "http://b:2", "http://c:3"]
        assert [b.token for b in bridges] == ["t1", "t2", "t3"]


# ---------------------------------------------------------------------------
# 4) MT5 mode activation — spawn a separate uvicorn subprocess on an
#    ephemeral port with MT5_BRIDGE_URL pointed at an unreachable address.
# ---------------------------------------------------------------------------
import socket
import subprocess
import time


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _MT5Server:
    def __init__(self):
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None

    def start(self):
        env = os.environ.copy()
        env["MT5_BRIDGE_URL"] = "http://127.0.0.1:9999"
        env["MT5_BRIDGE_TOKEN"] = "test-token"
        env.pop("MT5_BRIDGE_URLS", None)
        env.pop("MT5_BRIDGE_TOKENS", None)
        self.proc = subprocess.Popen(
            ["uvicorn", "server:app", "--host", "127.0.0.1",
             "--port", str(self.port), "--log-level", "warning"],
            cwd=str(BACKEND_DIR), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        # wait for ready
        deadline = time.time() + 25
        while time.time() < deadline:
            try:
                r = requests.get(f"http://127.0.0.1:{self.port}/api/kpis", timeout=2)
                if r.status_code < 500:
                    return
            except requests.RequestException:
                time.sleep(0.3)
        # surface logs if we failed
        out = b""
        if self.proc and self.proc.stdout:
            try:
                self.proc.stdout.close()
            except Exception:
                pass
        raise RuntimeError(f"MT5 mode server failed to start within 25s: {out!r}")

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


@pytest.fixture(scope="module")
def mt5_server():
    srv = _MT5Server()
    srv.start()
    yield srv
    srv.stop()


def _get(srv, path, **kw):
    return requests.get(srv.url(path), timeout=10, **kw)


def _post(srv, path, **kw):
    return requests.post(srv.url(path), timeout=10, **kw)


def _put(srv, path, **kw):
    return requests.put(srv.url(path), timeout=10, **kw)


class TestMT5ModeActivation:
    def test_kpis_mt5_source(self, mt5_server):
        r = _get(mt5_server, "/api/kpis")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("source") == "mt5"
        assert d["accounts_total"] == 0
        assert d["accounts_live"] == 0

    def test_accounts_empty_when_bridge_unreachable(self, mt5_server):
        r = _get(mt5_server, "/api/accounts")
        assert r.status_code == 200
        assert r.json() == []

    def test_bridge_health_unreachable(self, mt5_server):
        r = _get(mt5_server, "/api/bridge/health")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["configured"] == 1
        assert isinstance(d["bridges"], list) and len(d["bridges"]) == 1
        b = d["bridges"][0]
        assert b["url"] == "http://127.0.0.1:9999"
        assert b.get("status") == "unreachable"
        assert "error" in b

    def test_kill_switch_persists_when_bridge_down(self, mt5_server):
        r = _post(mt5_server, "/api/accounts/MT5-5609382/kill-switch",
                  json={"enabled": True})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["kill_switch"] is True
        assert d["status"] == "PAUSED"

        # GET account → bridge unreachable AND no cache yet → 503
        g = _get(mt5_server, "/api/accounts/MT5-5609382")
        assert g.status_code == 503

    def test_risk_limits_persist_and_merge(self, mt5_server):
        # First write
        r = _put(mt5_server, "/api/accounts/MT5-5609382/risk-limits",
                 json={"max_daily_loss_pct": 4.2})
        assert r.status_code == 200, r.text
        rl = r.json()["risk_limits"]
        assert rl["max_daily_loss_pct"] == 4.2
        assert "max_position_size_lots" in rl
        assert "max_open_positions" in rl

        # Patch another field — first should remain (merge behaviour)
        r2 = _put(mt5_server, "/api/accounts/MT5-5609382/risk-limits",
                  json={"max_open_positions": 11})
        assert r2.status_code == 200
        rl2 = r2.json()["risk_limits"]
        assert rl2["max_daily_loss_pct"] == 4.2
        assert rl2["max_open_positions"] == 11

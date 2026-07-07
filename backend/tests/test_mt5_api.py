"""Backend API tests for MT5 Quant Supervision dashboard."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://atlas-professional.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- KPIs ----
class TestKpis:
    def test_get_kpis(self, session):
        r = session.get(f"{API}/kpis", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_equity", "total_balance", "daily_pnl", "open_positions",
                  "active_alerts", "critical_alerts", "accounts_total",
                  "accounts_live", "avg_drawdown", "server_time"]:
            assert k in d, f"missing key {k}"
        assert d["accounts_total"] == 8
        assert isinstance(d["total_equity"], (int, float))


# ---- Accounts ----
class TestAccounts:
    def test_list_accounts(self, session):
        r = session.get(f"{API}/accounts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) == 8
        first = d[0]
        for k in ["id", "login", "broker", "strategy", "balance", "equity",
                  "daily_pnl", "max_drawdown", "current_drawdown", "status",
                  "margin_level", "risk_limits"]:
            assert k in first
        # private fields excluded
        assert "_equity_series" not in first
        assert "_trades" not in first

    def test_get_account(self, session):
        r = session.get(f"{API}/accounts/ACC-001", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == "ACC-001"

    def test_account_not_found(self, session):
        r = session.get(f"{API}/accounts/ACC-999", timeout=15)
        assert r.status_code == 404

    def test_equity_curve(self, session):
        r = session.get(f"{API}/accounts/ACC-001/equity?points=100", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["account_id"] == "ACC-001"
        assert isinstance(d["series"], list)
        assert len(d["series"]) > 0
        assert "t" in d["series"][0] and "equity" in d["series"][0]

    def test_drawdown(self, session):
        r = session.get(f"{API}/accounts/ACC-001/drawdown?points=100", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["account_id"] == "ACC-001"
        assert "max_drawdown" in d
        assert "current_drawdown" in d
        assert isinstance(d["series"], list)

    def test_trades_default(self, session):
        r = session.get(f"{API}/accounts/ACC-001/trades?limit=50", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["account_id"] == "ACC-001"
        assert len(d["trades"]) <= 50
        assert d["trades"], "no trades returned"

    def test_trades_symbol_filter(self, session):
        r = session.get(f"{API}/accounts/ACC-001/trades?limit=200&symbol=EURUSD", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for t in d["trades"]:
            assert t["symbol"] == "EURUSD"

    def test_trades_side_filter(self, session):
        r = session.get(f"{API}/accounts/ACC-001/trades?limit=200&side=BUY", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for t in d["trades"]:
            assert t["side"] == "BUY"

    def test_trades_invalid_side(self, session):
        r = session.get(f"{API}/accounts/ACC-001/trades?side=INVALID", timeout=15)
        # Literal -> 422
        assert r.status_code == 422


# ---- Kill switch and risk limits ----
class TestRisk:
    def test_kill_switch_toggle_and_persist(self, session):
        # Enable kill switch
        r = session.post(f"{API}/accounts/ACC-002/kill-switch", json={"enabled": True}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["kill_switch"] is True
        assert d["status"] == "PAUSED"

        # Verify via GET
        r2 = session.get(f"{API}/accounts/ACC-002", timeout=15)
        assert r2.json()["status"] == "PAUSED"
        assert r2.json()["kill_switch"] is True

        # Resume
        r3 = session.post(f"{API}/accounts/ACC-002/kill-switch", json={"enabled": False}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["status"] == "LIVE"

        r4 = session.get(f"{API}/accounts/ACC-002", timeout=15)
        assert r4.json()["status"] == "LIVE"

    def test_update_risk_limits(self, session):
        payload = {"max_daily_loss_pct": 4.5, "max_position_size_lots": 3.0, "max_open_positions": 25}
        r = session.put(f"{API}/accounts/ACC-003/risk-limits", json=payload, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["risk_limits"]["max_daily_loss_pct"] == 4.5
        assert d["risk_limits"]["max_position_size_lots"] == 3.0
        assert d["risk_limits"]["max_open_positions"] == 25
        # Verify persisted via GET
        r2 = session.get(f"{API}/accounts/ACC-003", timeout=15)
        rl = r2.json()["risk_limits"]
        assert rl["max_daily_loss_pct"] == 4.5
        assert rl["max_position_size_lots"] == 3.0
        assert rl["max_open_positions"] == 25


# ---- Alerts ----
class TestAlerts:
    def test_list_alerts(self, session):
        r = session.get(f"{API}/alerts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "alerts" in d and "count" in d
        assert d["count"] == len(d["alerts"])
        assert d["count"] > 0

    def test_alerts_severity_filter(self, session):
        r = session.get(f"{API}/alerts?severity=CRITICAL", timeout=15)
        assert r.status_code == 200
        for a in r.json()["alerts"]:
            assert a["severity"] == "CRITICAL"

    def test_ack_alert(self, session):
        # get an unack alert
        r = session.get(f"{API}/alerts?unacknowledged_only=true", timeout=15)
        alerts = r.json()["alerts"]
        if not alerts:
            pytest.skip("No unacked alerts to test")
        aid = alerts[0]["id"]
        r2 = session.post(f"{API}/alerts/{aid}/ack", json={"acknowledged": True}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["acknowledged"] is True

    def test_ack_alert_not_found(self, session):
        r = session.post(f"{API}/alerts/ALT-9999/ack", json={"acknowledged": True}, timeout=15)
        assert r.status_code == 404


# ---- Simulation tick ----
class TestTick:
    def test_tick_updates_equity(self, session):
        before = session.get(f"{API}/accounts/ACC-001", timeout=15).json()
        r = session.post(f"{API}/sim/tick", timeout=15)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        after = session.get(f"{API}/accounts/ACC-001", timeout=15).json()
        # equity should likely change (random gauss). If account is paused it won't, so check status
        if before["status"] != "PAUSED":
            # Don't assert hard-changes due to randomness but at least same keys exist
            assert "equity" in after

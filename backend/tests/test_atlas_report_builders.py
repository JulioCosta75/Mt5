"""Unit tests for per-account report builders (Phase 2 parts 1+2)."""
from __future__ import annotations

from atlas_reports import account_report_status, build_account_report
from atlas_store import scrub_secrets


class TestAccountReportBuilder:
    def test_never_ok_when_bridge_down(self):
        acc = {
            "id": "MT5-1",
            "login": 1,
            "broker": "Demo",
            "currency": "USD",
            "equity": 1000,
            "daily_pnl": 0,
            "open_positions": 0,
            "current_drawdown": 0.0,
            "status": "LIVE",
            "risk_limits": {"max_daily_loss_pct": 5.0},
        }
        assert account_report_status(acc, bridge_ok=False) == "WARNING"
        report = build_account_report(acc, source="auto", bridge_ok=False)
        assert report["status"] == "WARNING"
        assert report["account_id"] == "MT5-1"
        assert report["bridge_ok"] is False

    def test_error_account_is_alert(self):
        acc = {
            "id": "MT5-2",
            "login": 2,
            "broker": "Demo",
            "currency": "USD",
            "equity": 1000,
            "daily_pnl": 0,
            "open_positions": 0,
            "current_drawdown": 0.0,
            "status": "ERROR",
            "risk_limits": {},
        }
        assert account_report_status(acc, bridge_ok=True) == "ALERT"

    def test_stale_cache_never_ok(self):
        acc = {
            "id": "MT5-3",
            "login": 3,
            "status": "LIVE",
            "current_drawdown": 0.0,
            "risk_limits": {},
            "stale": True,
        }
        assert account_report_status(acc, bridge_ok=False) == "WARNING"

    def test_build_has_no_secret_fields(self):
        acc = {
            "id": "MT5-3",
            "login": 3,
            "broker": "Broker-X",
            "currency": "USD",
            "equity": 5000,
            "balance": 5000,
            "daily_pnl": 10,
            "open_positions": 1,
            "current_drawdown": -1.0,
            "max_drawdown": -2.0,
            "status": "LIVE",
            "risk_limits": {"max_daily_loss_pct": 3.0},
            "password": "leak",
        }
        report = build_account_report(acc, source="manual", bridge_ok=True)
        scrubbed = scrub_secrets(report)
        assert "password" not in scrubbed
        assert scrubbed["account_id"] == "MT5-3"
        assert scrubbed["metrics"]["equity"] == 5000
        assert scrubbed["data_origin"] == "live"

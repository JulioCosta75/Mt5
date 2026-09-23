"""Unit tests for per-account report builders (Phase 2 parts 1+2)."""
from __future__ import annotations

from atlas_reports import account_report_status, build_account_report, limits_status
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

    def test_open_positions_breach_is_warning_not_ok(self):
        """Live bug: status OK while limits_status showed breached open-positions."""
        acc = {
            "id": "MT5-62137776",
            "login": 62137776,
            "status": "LIVE",
            "current_drawdown": -0.5,
            "open_positions": 20,
            "risk_limits": {
                "max_daily_loss_pct": 5.0,
                "max_open_positions": 20,
                "max_position_size_lots": 1.0,
            },
        }
        positions = [
            {
                "symbol": "EURUSD",
                "type": 0,
                "volume": 0.1,
                "profit": 0,
                "swap": 0,
                "magic": 1,
                "ticket": i,
            }
            for i in range(20)
        ]
        assert (
            account_report_status(acc, bridge_ok=True, open_positions=positions)
            == "WARNING"
        )
        lim = limits_status(acc, open_positions=positions)
        assert lim["open_positions"]["breached"] is True
        assert lim["drawdown"]["breached"] is False
        report = build_account_report(
            acc, source="manual", bridge_ok=True, positions=positions
        )
        assert report["status"] == "WARNING"
        assert report["limits_status"]["open_positions"]["breached"] is True
        assert "breached open-positions limit" in report["message"]
        assert "status WARNING" in report["message"]

    def test_volume_breach_is_warning(self):
        acc = {
            "id": "MT5-9",
            "login": 9,
            "status": "LIVE",
            "current_drawdown": 0.0,
            "open_positions": 1,
            "risk_limits": {
                "max_daily_loss_pct": 5.0,
                "max_open_positions": 20,
                "max_position_size_lots": 1.0,
            },
        }
        positions = [
            {
                "symbol": "XAUUSD",
                "type": 0,
                "volume": 2.0,
                "profit": 0,
                "swap": 0,
                "magic": 1,
                "ticket": 1,
            }
        ]
        assert (
            account_report_status(acc, bridge_ok=True, open_positions=positions)
            == "WARNING"
        )

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

"""Unit tests for supervision snapshot aggregation."""
from supervision_snapshot import build_supervision_snapshot

MOCK_ACCOUNTS = [
    {"equity": 100000, "balance": 100000, "daily_pnl": -100, "open_positions": 1,
     "status": "LIVE", "current_drawdown": -1.0, "risk_limits": {"max_daily_loss_pct": 3.0}},
]
MOCK_ALERTS = [
    {"severity": "CRITICAL", "acknowledged": False},
]


def test_mock_mode_preserves_sample_counts():
    snap = build_supervision_snapshot(MOCK_ACCOUNTS, MOCK_ALERTS, mode="mock", bridge_ok=None)
    assert snap["mode"] == "mock"
    assert snap["accounts"]["total"] == 1
    assert snap["alerts"]["critical"] == 1


def test_mt5_mode_empty_feed_has_zero_alerts():
    snap = build_supervision_snapshot([], [], mode="mt5", bridge_ok=False)
    assert snap["mode"] == "mt5"
    assert snap["accounts"]["total"] == 0
    assert snap["alerts"]["active"] == 0
    assert snap["services"]["bridge_ok"] is False
    assert "MT5" in snap["message"]


def test_mt5_mode_live_accounts_only():
    live = [{"equity": 990.99, "balance": 1000, "daily_pnl": -9.01, "open_positions": 0,
             "status": "LIVE", "current_drawdown": 0, "risk_limits": {"max_daily_loss_pct": 3.0},
             "id": "MT5-62127915"}]
    snap = build_supervision_snapshot(live, [], mode="mt5", bridge_ok=True)
    assert snap["kpis"]["total_equity"] == 990.99
    assert snap["accounts"]["total"] == 1
    assert snap["accounts"]["live"] == 1
    assert snap["alerts"]["active"] == 0

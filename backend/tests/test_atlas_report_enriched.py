"""Part 3 — enriched per-account report content (no FastAPI required)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from atlas_reports import (
    build_account_report,
    closed_trades_since,
    compare_with_previous,
    factual_conclusion,
    limits_status,
    summarize_open_positions,
)
from atlas_store import scrub_secrets


def _acc(**over):
    base = {
        "id": "MT5-1001",
        "login": 1001,
        "broker": "Demo-Server",
        "currency": "USD",
        "equity": 10500.0,
        "balance": 10000.0,
        "daily_pnl": 50.0,
        "open_positions": 2,
        "current_drawdown": -1.5,
        "max_drawdown": -3.0,
        "status": "LIVE",
        "risk_limits": {
            "max_daily_loss_pct": 3.0,
            "max_open_positions": 5,
            "max_position_size_lots": 1.0,
        },
    }
    base.update(over)
    return base


SAMPLE_POSITIONS = [
    {
        "ticket": 1,
        "symbol": "XAUUSD",
        "side": "BUY",
        "volume": 0.2,
        "profit": 12.5,
        "swap": -0.5,
        "magic": 42,
    },
    {
        "ticket": 2,
        "symbol": "EURUSD",
        "side": "SELL",
        "volume": 1.5,
        "profit": -3.0,
        "swap": 0.0,
        "magic": 42,
    },
]


def _deal(ticket, *, pos_id, side, volume, price, profit, time_iso, magic=42, entry=True):
    return {
        "ticket": ticket,
        "order": ticket,
        "position_id": pos_id,
        "symbol": "XAUUSD",
        "side": side,
        "volume": volume,
        "price": price,
        "profit": profit,
        "swap": 0.0,
        "commission": 0.0,
        "magic": magic,
        "comment": "scalper",
        "time": time_iso,
        "entry": 0 if entry else 1,
    }


class TestSummarizePositions:
    def test_open_position_fields(self):
        rows = summarize_open_positions(SAMPLE_POSITIONS)
        assert len(rows) == 2
        assert rows[0]["symbol"] == "XAUUSD"
        assert rows[0]["side"] == "BUY"
        assert rows[0]["volume"] == 0.2
        assert rows[0]["floating_pnl"] == 12.0  # 12.5 - 0.5


class TestClosedSincePrevious:
    def test_only_trades_after_previous_timestamp(self):
        t0 = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        trades = [
            {
                "symbol": "XAUUSD",
                "side": "BUY",
                "pnl": 10.0,
                "lots": 0.1,
                "close_time": (t0 + timedelta(hours=1)).isoformat(),
                "magic": 1,
            },
            {
                "symbol": "EURUSD",
                "side": "SELL",
                "pnl": -2.0,
                "lots": 0.2,
                "close_time": (t0 - timedelta(hours=1)).isoformat(),
                "magic": 1,
            },
        ]
        got = closed_trades_since(trades, since_iso=t0.isoformat())
        assert len(got) == 1
        assert got[0]["symbol"] == "XAUUSD"
        assert got[0]["pnl"] == 10.0

    def test_no_previous_means_empty_delta_list(self):
        assert closed_trades_since([{"close_time": "2026-01-01T00:00:00+00:00"}], since_iso=None) == []


class TestLimitsAndComparison:
    def test_limits_detect_volume_and_drawdown_breach(self):
        acc = _acc(current_drawdown=-4.0)  # abs 4 >= 3
        lim = limits_status(acc, open_positions=summarize_open_positions(SAMPLE_POSITIONS))
        assert lim["drawdown"]["breached"] is True
        assert lim["open_positions"]["current"] == 2
        assert lim["open_positions"]["breached"] is False
        assert lim["position_volume"]["largest_open_lots"] == 1.5
        assert lim["position_volume"]["breached"] is True  # 1.5 >= 1.0

    def test_comparison_same_account_only(self):
        acc = _acc(equity=11000.0, daily_pnl=100.0, open_positions=1, current_drawdown=-0.5)
        prev = {
            "id": "prev-1",
            "account_id": "MT5-1001",
            "created_at": "2026-08-01T00:00:00+00:00",
            "bridge_ok": True,
            "metrics": {
                "equity": 10500.0,
                "daily_pnl": 50.0,
                "open_positions": 2,
                "current_drawdown": -1.5,
            },
        }
        cmp_ = compare_with_previous(acc, prev, bridge_ok=True)
        assert cmp_ is not None
        assert cmp_["equity"]["delta"] == 500.0
        assert cmp_["open_positions"]["delta"] == -1.0
        assert cmp_["bridge_link"] == "unchanged"

        other = dict(prev)
        other["account_id"] = "MT5-OTHER"
        assert compare_with_previous(acc, other, bridge_ok=True) is None


class TestBuildEnrichedReport:
    def test_enriched_fields_and_conclusion(self):
        t_entry = "2026-08-20T08:00:00+00:00"
        t_exit = "2026-08-20T10:00:00+00:00"
        deals = [
            _deal(1, pos_id=9, side="BUY", volume=0.1, price=2400.0, profit=0.0, time_iso=t_entry),
            _deal(2, pos_id=9, side="SELL", volume=0.1, price=2410.0, profit=25.0, time_iso=t_exit, entry=False),
        ]
        previous = {
            "id": "r0",
            "account_id": "MT5-1001",
            "created_at": "2026-08-19T00:00:00+00:00",
            "bridge_ok": True,
            "metrics": {
                "equity": 10000.0,
                "daily_pnl": 0.0,
                "open_positions": 0,
                "current_drawdown": 0.0,
            },
        }
        report = build_account_report(
            _acc(),
            source="auto",
            bridge_ok=True,
            positions=SAMPLE_POSITIONS,
            deals=deals,
            previous_report=previous,
        )
        assert report["account_id"] == "MT5-1001"
        assert report["snapshot_at"]
        assert report["data_origin"] == "live"
        assert report["account_type"] == "not_available"
        assert report["session"] == "not_available"
        assert len(report["open_positions"]) == 2
        assert report["open_positions"][0]["symbol"] == "XAUUSD"
        assert len(report["closed_trades_since_previous"]) == 1
        assert report["closed_trades_since_previous"][0]["pnl"] == 25.0
        assert "limits_status" in report
        assert report["comparison_to_previous"]["equity"]["delta"] == 500.0
        assert "conclusion" in report and report["conclusion"]
        assert "Account 1001" in report["conclusion"]
        # secrets scrub still clean
        assert "password" not in scrub_secrets(report)

    def test_cross_account_previous_ignored(self):
        previous = {
            "id": "r-other",
            "account_id": "MT5-9999",
            "created_at": "2026-08-01T00:00:00+00:00",
            "metrics": {"equity": 1.0, "daily_pnl": 0, "open_positions": 0, "current_drawdown": 0},
        }
        report = build_account_report(
            _acc(),
            source="auto",
            bridge_ok=True,
            positions=[],
            deals=[],
            previous_report=previous,
        )
        assert report["comparison_to_previous"] is None
        assert report["closed_trades_since_previous"] == []

    def test_factual_conclusion_mentions_bridge_down(self):
        text = factual_conclusion(
            _acc(),
            status="WARNING",
            limits=limits_status(_acc(), open_positions=[]),
            comparison=None,
            closed_count=0,
            bridge_ok=False,
        )
        assert "bridge unavailable" in text

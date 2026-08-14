"""Unit tests for EA naming / grouping (mt5_adapter)."""
from __future__ import annotations

from mt5_adapter import (
    comment_is_usable,
    eas_from_bridge,
    resolve_ea_label,
    trades_from_deals,
)


def test_comment_is_usable_filters_junk():
    assert comment_is_usable("Dark Mimas") is True
    assert comment_is_usable("  ") is False
    assert comment_is_usable("12345") is False
    assert comment_is_usable("from #998877") is False
    assert comment_is_usable(None) is False


def test_resolve_label_priority_manual_comment_fallback():
    label, src = resolve_ea_label(42, ["Dark Mimas"] * 5, override="Meu nome")
    assert label == "Meu nome" and src == "manual"

    label, src = resolve_ea_label(42, ["Dark Mimas"] * 4 + ["other"], override=None)
    assert label == "Dark Mimas" and src == "comment"

    # Below 60% consistency → fallback
    label, src = resolve_ea_label(42, ["A", "B", "C"], override=None)
    assert label == "EA 42" and src == "fallback"

    label, src = resolve_ea_label(0, ["anything"], override=None)
    assert label == "Manual / sem EA" and src == "manual_zero"


def test_eas_from_bridge_groups_by_magic():
    positions = [
        {"magic": 100, "comment": "Dark Mimas", "profit": 10.0, "swap": 0.0, "symbol": "EURUSD"},
        {"magic": 100, "comment": "Dark Mimas", "profit": -2.0, "swap": 0.0, "symbol": "GBPUSD"},
        {"magic": 200, "comment": "", "profit": 1.0, "swap": 0.0, "symbol": "XAUUSD"},
    ]
    deals = [
        {
            "ticket": 1, "position_id": 10, "magic": 100, "comment": "Dark Mimas",
            "symbol": "EURUSD", "side": "BUY", "volume": 0.1, "price": 1.1,
            "profit": 0, "swap": 0, "commission": 0, "time": "2026-01-01T10:00:00+00:00",
        },
        {
            "ticket": 2, "position_id": 10, "magic": 100, "comment": "Dark Mimas",
            "symbol": "EURUSD", "side": "SELL", "volume": 0.1, "price": 1.2,
            "profit": 50.0, "swap": 0, "commission": -1.0, "time": "2026-01-01T12:00:00+00:00",
        },
    ]
    rows = eas_from_bridge(
        account_id="MT5-1",
        login=1,
        positions=positions,
        deals=deals,
        label_overrides={},
    )
    by_magic = {r["magic"]: r for r in rows}
    assert by_magic[100]["label"] == "Dark Mimas"
    assert by_magic[100]["label_source"] == "comment"
    assert by_magic[100]["open_positions"] == 2
    assert by_magic[100]["floating_pnl"] == 8.0
    assert by_magic[100]["realized_pnl"] == 49.0
    assert by_magic[100]["trade_count"] == 1
    assert by_magic[200]["label"] == "EA 200"
    assert by_magic[200]["label_source"] == "fallback"


def test_trades_from_deals_includes_magic_and_label():
    deals = [
        {
            "ticket": 1, "position_id": 7, "magic": 55, "comment": "BotX",
            "symbol": "EURUSD", "side": "BUY", "volume": 0.2, "price": 1.0,
            "profit": 0, "swap": 0, "commission": 0, "time": "2026-02-01T10:00:00+00:00",
        },
        {
            "ticket": 2, "position_id": 7, "magic": 55, "comment": "BotX",
            "symbol": "EURUSD", "side": "SELL", "volume": 0.2, "price": 1.1,
            "profit": 20.0, "swap": 0, "commission": 0, "time": "2026-02-01T11:00:00+00:00",
        },
    ]
    rows = trades_from_deals(deals, label_overrides={55: "Renamed"})
    assert len(rows) == 1
    assert rows[0]["magic"] == 55
    assert rows[0]["strategy"] == "Renamed"

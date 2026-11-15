"""Cached (stale) accounts must never be shown as LIVE (founder authorization 2026-11-14).

In-process only: no MT5, no bridge.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import mt5_adapter  # noqa: E402
import atlas_alerts  # noqa: E402

LIVE_SNAPSHOT = {
    "id": "MT5-123", "login": 123, "status": "LIVE", "connected": True,
    "trade_allowed": True, "balance": 1000.0, "equity": 990.0,
    "current_drawdown": 0.0, "risk_limits": {},
}


def test_mark_stale_is_offline_and_keeps_values():
    out = mt5_adapter.mark_stale(LIVE_SNAPSHOT)
    assert out["status"] == "OFFLINE" and out["stale"] is True and out["connected"] is False
    assert out["equity"] == 990.0 and out["balance"] == 1000.0
    assert LIVE_SNAPSHOT["status"] == "LIVE"  # the cached copy is not mutated


def test_stale_account_raises_only_the_bridge_alert():
    out = mt5_adapter.mark_stale(LIVE_SNAPSHOT)
    keys = {a["rule_key"] for a in atlas_alerts.evaluate_account_conditions(out, bridge_ok=False)}
    assert atlas_alerts.RULE_BRIDGE_DOWN in keys
    assert atlas_alerts.RULE_ACCOUNT_ERROR not in keys


def test_server_fallback_serves_cached_accounts_as_offline(monkeypatch):
    import server
    import mt5_client

    class Cursor:
        def __init__(self, docs):
            self.docs = docs

        async def to_list(self, _n):
            return self.docs

    class Coll:
        def find(self, *_a, **_k):
            return Cursor([{"payload": dict(LIVE_SNAPSHOT)}])

    class Cache:
        cache = Coll()

    monkeypatch.setattr(server, "_cache", Cache())
    monkeypatch.setattr(mt5_client, "clients", lambda: [])
    accounts, ok = asyncio.run(server._mt5_live_accounts())
    assert ok is False
    assert [a["status"] for a in accounts] == ["OFFLINE"]
    assert accounts[0]["stale"] is True

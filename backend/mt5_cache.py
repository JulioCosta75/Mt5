"""MongoDB-backed cache for MT5 data.

Two purposes:

1. **Fallback**: when the bridge is unreachable, return the last successful
   snapshot so the dashboard keeps showing something instead of breaking.

2. **Per-account persistence**: kill-switch state and risk-limit overrides
   live in Mongo (the bridge does not know about them).

Documents:

  Collection `mt5_cache`:
    { _id: "account:<login>",  payload: {...account...},  fetched_at: iso }
    { _id: "deals:<login>",    payload: [...],            fetched_at: iso }
    { _id: "equity:<login>",   payload: [...series...],   fetched_at: iso }
    { _id: "positions:<login>",payload: [...],            fetched_at: iso }
    { _id: "orders:<login>",   payload: [...],            fetched_at: iso }

  Collection `mt5_overrides`:
    { _id: <login>,
      kill_switch: false,
      risk_limits: { max_daily_loss_pct, max_position_size_lots, max_open_positions },
      daily_pnl_anchor: { date: "YYYY-MM-DD", balance: float } }
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

_DEFAULT_LIMITS = {
    "max_daily_loss_pct": 3.0,
    "max_position_size_lots": 1.0,
    "max_open_positions": 20,
}


class MT5Cache:
    def __init__(self, db):
        self.db = db
        self.cache = db["mt5_cache"]
        self.overrides = db["mt5_overrides"]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ---- generic cache ----
    async def put(self, key: str, payload: Any) -> None:
        await self.cache.update_one(
            {"_id": key},
            {"$set": {"payload": payload, "fetched_at": self._now_iso()}},
            upsert=True,
        )

    async def get(self, key: str) -> dict | None:
        doc = await self.cache.find_one({"_id": key}, {"_id": 0})
        return doc

    # ---- overrides ----
    async def get_overrides(self, login: int) -> dict:
        doc = await self.overrides.find_one({"_id": login})
        if not doc:
            doc = {
                "_id": login,
                "kill_switch": False,
                "risk_limits": dict(_DEFAULT_LIMITS),
                "daily_pnl_anchor": None,
            }
            await self.overrides.insert_one(doc)
        return {
            "kill_switch": doc.get("kill_switch", False),
            "risk_limits": doc.get("risk_limits", dict(_DEFAULT_LIMITS)),
            "daily_pnl_anchor": doc.get("daily_pnl_anchor"),
        }

    async def set_kill_switch(self, login: int, enabled: bool) -> None:
        await self.overrides.update_one(
            {"_id": login}, {"$set": {"kill_switch": enabled}}, upsert=True,
        )

    async def update_risk_limits(self, login: int, patch: dict) -> dict:
        ov = await self.get_overrides(login)
        merged = {**ov["risk_limits"], **{k: v for k, v in patch.items() if v is not None}}
        await self.overrides.update_one(
            {"_id": login}, {"$set": {"risk_limits": merged}}, upsert=True,
        )
        return merged

    async def maybe_set_daily_anchor(self, login: int, balance: float) -> float:
        """Anchor today's starting balance once per UTC day. Returns the anchor."""
        today = datetime.now(timezone.utc).date().isoformat()
        ov = await self.overrides.find_one({"_id": login}) or {}
        anchor = ov.get("daily_pnl_anchor")
        if not anchor or anchor.get("date") != today:
            anchor = {"date": today, "balance": float(balance)}
            await self.overrides.update_one(
                {"_id": login}, {"$set": {"daily_pnl_anchor": anchor}}, upsert=True,
            )
        return float(anchor["balance"])

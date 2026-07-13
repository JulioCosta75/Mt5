"""Shared MT5 live-data fetchers used by API routes and supervision snapshots."""
from __future__ import annotations

import logging

import httpx

from mt5_adapter import account_from_bridge, drawdown_from_equity
from mt5_client import BridgeClient, clients

logger = logging.getLogger("mt5-live")


class MT5LiveData:
    def __init__(self, cache):
        self.cache = cache

    async def _try_account(self, client: BridgeClient) -> dict | None:
        try:
            return await client.account()
        except (httpx.HTTPError, httpx.HTTPStatusError) as e:
            logger.warning("bridge %s account fetch failed: %s", client.endpoint.url, e)
            return None

    async def _enriched_account(self, client: BridgeClient, bridge_account: dict) -> dict:
        login = int(bridge_account["login"])
        try:
            positions = await client.positions()
        except httpx.HTTPError:
            positions = []
        overrides = await self.cache.get_overrides(login)
        anchor_balance = await self.cache.maybe_set_daily_anchor(
            login, bridge_account.get("balance", 0.0)
        )

        eq_doc = await self.cache.get(f"equity:{login}")
        series = (eq_doc or {}).get("payload", {}).get("series", []) or []
        _, max_dd, current_dd = drawdown_from_equity(series)

        acc = account_from_bridge(
            bridge_account,
            positions_count=len(positions),
            risk_limits=overrides["risk_limits"],
            kill_switch=overrides["kill_switch"],
            max_dd=max_dd,
            current_dd=current_dd,
            daily_pnl_anchor=anchor_balance,
        )
        await self.cache.put(f"account:{login}", acc)
        return acc

    async def list_accounts(self) -> list[dict]:
        out: list[dict] = []
        any_reachable = False
        for client in clients():
            bridge_acc = await self._try_account(client)
            if bridge_acc:
                any_reachable = True
                out.append(await self._enriched_account(client, bridge_acc))
        if not any_reachable:
            cached_keys = await self.cache.cache.find(
                {"_id": {"$regex": r"^account:MT5-"}}, {"_id": 0}
            ).to_list(50)
            for doc in cached_keys:
                payload = doc.get("payload")
                if payload and str(payload.get("id", "")).startswith("MT5-"):
                    payload = dict(payload)
                    payload["stale"] = True
                    out.append(payload)
        return out

    async def bridge_reachable(self) -> bool:
        bridges = clients()
        if not bridges:
            return False
        try:
            health = await bridges[0].health()
            return bool(health.get("terminal_connected"))
        except (httpx.HTTPError, Exception):  # noqa: BLE001
            return False

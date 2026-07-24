"""Routes that bridge the existing /api/* contract to real MT5 data.

Strategy: the public URL/contract stays identical to the mock version, so the
React frontend keeps working. We resolve account IDs via MT5 logins (id of the
form `MT5-<login>`).
"""
from __future__ import annotations

import logging
from typing import Optional, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mt5_adapter import (
    drawdown_from_equity,
    orders_passthrough,
    positions_passthrough,
    trades_from_deals,
)
from mt5_client import BridgeClient, clients
from mt5_live import MT5LiveData

logger = logging.getLogger("mt5-routes")


class KillSwitchPayload(BaseModel):
    enabled: bool


class RiskLimitsPayload(BaseModel):
    max_daily_loss_pct: Optional[float] = None
    max_position_size_lots: Optional[float] = None
    max_open_positions: Optional[int] = None


class AckAlertPayload(BaseModel):
    acknowledged: bool = True


def build_router(cache) -> APIRouter:
    """Factory that wires the routes against the provided cache."""
    live = MT5LiveData(cache)
    router = APIRouter(prefix="/api")

    async def _try_account(client: BridgeClient) -> dict | None:
        return await live._try_account(client)

    async def _resolve_login_to_client(login: int) -> BridgeClient | None:
        for c in clients():
            acc = await _try_account(c)
            if acc and int(acc.get("login", -1)) == login:
                return c
        return None

    @router.get("/accounts")
    async def list_accounts():
        return await live.list_accounts()

    @router.get("/accounts/{account_id}")
    async def get_account(account_id: str):
        if not account_id.startswith("MT5-"):
            raise HTTPException(404, "unknown account id")
        login = int(account_id.removeprefix("MT5-"))
        client = await _resolve_login_to_client(login)
        if not client:
            cached = await cache.get(f"account:{login}")
            if cached:
                p = cached["payload"]
                p["stale"] = True
                return p
            raise HTTPException(503, "bridge unreachable and no cache")
        bridge_acc = await _try_account(client)
        if not bridge_acc:
            cached = await cache.get(f"account:{login}")
            if cached:
                p = cached["payload"]
                p["stale"] = True
                return p
            raise HTTPException(503, "bridge unreachable")
        return await live._enriched_account(client, bridge_acc)

    @router.get("/accounts/{account_id}/equity")
    async def equity(account_id: str, points: int = 200):
        login = int(account_id.removeprefix("MT5-"))
        client = await _resolve_login_to_client(login)
        if client:
            try:
                hist = await client.equity_history(days=90)
                series = hist.get("series", [])
                await cache.put(f"equity:{login}", {"series": series})
            except httpx.HTTPError as e:
                logger.warning("equity_history failed: %s", e)
                series = (await cache.get(f"equity:{login}") or {}).get("payload", {}).get("series", [])
        else:
            series = (await cache.get(f"equity:{login}") or {}).get("payload", {}).get("series", [])
        if points and len(series) > points:
            step = max(1, len(series) // points)
            series = series[::step]
        return {"account_id": account_id, "series": series}

    @router.get("/accounts/{account_id}/drawdown")
    async def drawdown(account_id: str, points: int = 200):
        login = int(account_id.removeprefix("MT5-"))
        series_doc = await cache.get(f"equity:{login}")
        series = (series_doc or {}).get("payload", {}).get("series", [])
        dd_series, max_dd, current_dd = drawdown_from_equity(series)
        if points and len(dd_series) > points:
            step = max(1, len(dd_series) // points)
            dd_series = dd_series[::step]
        return {
            "account_id": account_id,
            "series": dd_series,
            "max_drawdown": max_dd,
            "current_drawdown": current_dd,
        }

    @router.get("/accounts/{account_id}/trades")
    async def trades(account_id: str, limit: int = 50,
                     symbol: Optional[str] = None,
                     side: Optional[Literal["BUY", "SELL"]] = None):
        login = int(account_id.removeprefix("MT5-"))
        client = await _resolve_login_to_client(login)
        rows: list[dict] = []
        if client:
            try:
                deals_raw = await client.deals(days=90)
                rows = trades_from_deals(deals_raw)
                await cache.put(f"trades:{login}", rows)
            except httpx.HTTPError as e:
                logger.warning("deals fetch failed: %s", e)
                rows = (await cache.get(f"trades:{login}") or {}).get("payload", [])
        else:
            rows = (await cache.get(f"trades:{login}") or {}).get("payload", [])
        if symbol:
            rows = [t for t in rows if t["symbol"] == symbol]
        if side:
            rows = [t for t in rows if t["side"] == side]
        return {"account_id": account_id, "count": len(rows), "trades": rows[:limit]}

    @router.get("/accounts/{account_id}/positions")
    async def positions(account_id: str):
        login = int(account_id.removeprefix("MT5-"))
        client = await _resolve_login_to_client(login)
        if client:
            try:
                ps = await client.positions()
                await cache.put(f"positions:{login}", ps)
                return {"account_id": account_id, "positions": positions_passthrough(ps)}
            except httpx.HTTPError as e:
                logger.warning("positions fetch failed: %s", e)
        cached = await cache.get(f"positions:{login}")
        return {"account_id": account_id, "positions": (cached or {}).get("payload", []), "stale": True}

    @router.get("/accounts/{account_id}/orders")
    async def orders(account_id: str):
        login = int(account_id.removeprefix("MT5-"))
        client = await _resolve_login_to_client(login)
        if client:
            try:
                os_ = await client.orders()
                await cache.put(f"orders:{login}", os_)
                return {"account_id": account_id, "orders": orders_passthrough(os_)}
            except httpx.HTTPError as e:
                logger.warning("orders fetch failed: %s", e)
        cached = await cache.get(f"orders:{login}")
        return {"account_id": account_id, "orders": (cached or {}).get("payload", []), "stale": True}

    @router.post("/accounts/{account_id}/kill-switch")
    async def kill_switch(account_id: str, payload: KillSwitchPayload):
        login = int(account_id.removeprefix("MT5-"))
        await cache.set_kill_switch(login, payload.enabled)
        cached = await cache.get(f"account:{login}")
        if cached:
            cached["payload"]["kill_switch"] = payload.enabled
            cached["payload"]["status"] = "PAUSED" if payload.enabled else cached["payload"].get("status")
            await cache.put(f"account:{login}", cached["payload"])
        return {"account_id": account_id, "kill_switch": payload.enabled,
                "status": "PAUSED" if payload.enabled else "LIVE",
                "note": "advisory only — Phase 2 will close live positions via bridge"}

    @router.put("/accounts/{account_id}/risk-limits")
    async def update_risk(account_id: str, payload: RiskLimitsPayload):
        login = int(account_id.removeprefix("MT5-"))
        merged = await cache.update_risk_limits(login, payload.model_dump(exclude_none=True))
        return {"account_id": account_id, "risk_limits": merged}

    @router.get("/")
    async def root():
        return {"service": "MT5 Quant Supervision API", "status": "ok", "source": "mt5"}

    @router.get("/alerts")
    async def list_alerts(severity: Optional[str] = None, unacknowledged_only: bool = False):
        items: list[dict] = []
        if severity:
            items = [a for a in items if a.get("severity") == severity.upper()]
        if unacknowledged_only:
            items = [a for a in items if not a.get("acknowledged")]
        return {"count": len(items), "alerts": items}

    @router.post("/alerts/{alert_id}/ack")
    async def ack_alert(alert_id: str, payload: AckAlertPayload):
        raise HTTPException(status_code=404, detail="Alert not found")

    @router.post("/sim/tick")
    async def tick():
        return {"ok": True, "server_time": await _server_time(), "source": "mt5"}

    @router.get("/kpis")
    async def kpis():
        accs = await live.list_accounts()
        total_equity = sum(a.get("equity", 0) for a in accs)
        total_balance = sum(a.get("balance", 0) for a in accs)
        daily_pnl = sum(a.get("daily_pnl", 0) for a in accs)
        open_positions = sum(a.get("open_positions", 0) for a in accs)
        live_count = sum(1 for a in accs if a.get("status") == "LIVE")
        avg_dd = round(sum(a.get("current_drawdown", 0) for a in accs) / max(len(accs), 1), 2) if accs else 0.0
        return {
            "total_equity": round(total_equity, 2),
            "total_balance": round(total_balance, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl / total_equity * 100, 2) if total_equity else 0.0,
            "open_positions": open_positions,
            "active_alerts": 0,
            "critical_alerts": 0,
            "accounts_total": len(accs),
            "accounts_live": live_count,
            "avg_drawdown": avg_dd,
            "server_time": (await _server_time()),
            "source": "mt5",
        }

    @router.get("/bridge/health")
    async def bridge_health():
        out = []
        for c in clients():
            try:
                out.append({"url": c.endpoint.url, **(await c.health())})
            except httpx.HTTPError as e:
                out.append({"url": c.endpoint.url, "status": "unreachable", "error": str(e)})
        return {"bridges": out, "configured": len(out)}

    router._mt5_live = live  # type: ignore[attr-defined]
    return router


async def _server_time() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

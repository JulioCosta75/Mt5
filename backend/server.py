from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import asyncio
import logging
import math
import random
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ------------------------------------------------------------
# Build / version info — so the running deployment can be
# verified from the Dashboard and health endpoint. This is the
# single source of truth for "which build is running".
#
# Resolution order (first hit wins):
#   1. Environment overrides ATLAS_VERSION / ATLAS_BUILD
#      (set by the Windows installer service definition).
#   2. build_info.json  — written by installer/build.bat at build
#      time (version + UTC build timestamp + git short SHA).
#   3. VERSION           — committed plain-text fallback.
#   4. Hard-coded default.
# ------------------------------------------------------------
def _load_build_info() -> dict:
    import json
    info = {"version": "0.0.0-dev", "build": "local", "built_at": None, "channel": "dev"}
    # 2) build_info.json (produced by the installer build step)
    try:
        bi_path = ROOT_DIR / "build_info.json"
        if bi_path.exists():
            data = json.loads(bi_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                info.update({k: v for k, v in data.items() if v is not None})
    except Exception as e:  # noqa: BLE001
        logging.getLogger("server").warning("Could not read build_info.json: %s", e)
    # 3) VERSION file fallback (only if build_info.json didn't set a version)
    if info["version"] in (None, "", "0.0.0-dev"):
        try:
            ver_path = ROOT_DIR / "VERSION"
            if ver_path.exists():
                v = ver_path.read_text(encoding="utf-8").strip()
                if v:
                    info["version"] = v
                    if info.get("build") in (None, "", "local"):
                        info["build"] = "release"
                    if info.get("channel") == "dev":
                        info["channel"] = "release"
        except Exception as e:  # noqa: BLE001
            logging.getLogger("server").warning("Could not read VERSION file: %s", e)
    # 1) Environment overrides (highest priority — set by the installer)
    if os.environ.get("ATLAS_VERSION"):
        info["version"] = os.environ["ATLAS_VERSION"].strip()
    if os.environ.get("ATLAS_BUILD"):
        info["build"] = os.environ["ATLAS_BUILD"].strip()
    return info


BUILD_INFO = _load_build_info()

# ------------------------------------------------------------
# Storage backend selection.
#   ATLAS_STORE=mongo   (default, Linux/Emergent)
#   ATLAS_STORE=sqlite  (Windows installer, no Mongo needed)
# ------------------------------------------------------------
ATLAS_STORE = os.environ.get("ATLAS_STORE", "mongo").lower()

# Phase 2 — automatic supervision snapshot scheduler.
# When > 0, a background task persists a per-account supervision report
# (source="auto") every N seconds. Preview default stays 0 (disabled) so
# the preview DB stays clean; Windows installer sets 1800 (30 minutes).
# On-demand capture remains available via POST /api/supervision/auto-snapshot.
try:
    AUTO_SNAPSHOT_INTERVAL_SEC = int(os.environ.get("ATLAS_AUTO_SNAPSHOT_INTERVAL_SEC", "0"))
except ValueError:
    AUTO_SNAPSHOT_INTERVAL_SEC = 0

# How long to keep persisted Sr. Atlas reports (days). Purge runs in the
# background and never blocks backend startup.
try:
    REPORT_RETENTION_DAYS = int(os.environ.get("ATLAS_REPORT_RETENTION_DAYS", "90"))
except ValueError:
    REPORT_RETENTION_DAYS = 90

mongo_db = None
if ATLAS_STORE == "mongo":
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    mongo_client = AsyncIOMotorClient(mongo_url)
    mongo_db = mongo_client[os.environ.get("DB_NAME", "test_database")]

app = FastAPI(title="Atlas — MT5 Supervision API")
api_router = APIRouter(prefix="/api")

# ------------------------------------------------------------
# Phase 2 — Sr. Atlas supervision report store.
# Mongo (preview), SQLite (Windows installer — same atlas.db as MT5 cache),
# or in-memory fallback. Every report is scoped to one account_id.
# ------------------------------------------------------------
from atlas_store import AtlasReportStore
from atlas_reports import account_report_status, build_account_report

_sqlite_path = os.environ.get("ATLAS_SQLITE_PATH", str(ROOT_DIR / "data" / "atlas.db"))
if ATLAS_STORE == "sqlite":
    _atlas_store = AtlasReportStore(sqlite_path=_sqlite_path)
elif mongo_db is not None:
    _atlas_store = AtlasReportStore(mongo_db)
else:
    _atlas_store = AtlasReportStore()

# ------------------------------------------------------------
# Operating mode: if any MT5_BRIDGE_URL is configured we serve
# REAL data via routes_mt5; otherwise we keep the mock data
# below for development / preview.
# ------------------------------------------------------------
MT5_MODE = bool(os.environ.get("MT5_BRIDGE_URL") or os.environ.get("MT5_BRIDGE_URLS"))

# ------------------------------------------------------------
# In-memory state (mock data). Generated deterministically on
# startup so the UI feels stable but realistic. A `tick` endpoint
# advances simulated equity/PnL to convey real-time feel.
# ------------------------------------------------------------

random.seed(7)

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "USDCAD", "AUDUSD", "BTCUSD", "NAS100", "US30", "DAX40"]
STRATEGIES = ["Mean-Reversion v3", "Trend Follow Alpha", "Grid Hedge", "News Scalper", "Range Breakout", "ML-Momentum"]
BROKERS = ["ICMarkets-Live01", "Pepperstone-Live", "Darwinex-Live", "FTMO-Live", "BlueberryMarkets-Live"]


def _gen_equity_series(start_equity: float, days: int = 90, vol: float = 0.008, drift: float = 0.0009, seed: int = 0):
    rng = random.Random(seed)
    values = []
    equity = start_equity
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    for i in range(days * 4):  # 4 points/day
        ts = start + timedelta(hours=6 * i)
        # geometric brownian-ish
        shock = rng.gauss(drift, vol)
        equity = max(1000.0, equity * (1 + shock))
        values.append({"t": ts.isoformat(), "equity": round(equity, 2)})
    return values


def _drawdown_from_equity(series):
    peak = -math.inf
    out = []
    max_dd = 0.0
    for p in series:
        peak = max(peak, p["equity"])
        dd = (p["equity"] - peak) / peak * 100.0 if peak > 0 else 0.0
        max_dd = min(max_dd, dd)
        out.append({"t": p["t"], "dd": round(dd, 3)})
    return out, round(max_dd, 2)


def _gen_trades(account_id: str, n: int = 120, seed: int = 0):
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    trades = []
    for i in range(n):
        sym = rng.choice(SYMBOLS)
        side = rng.choice(["BUY", "SELL"])
        lots = round(rng.choice([0.01, 0.05, 0.1, 0.25, 0.5, 1.0]), 2)
        pnl = round(rng.gauss(8, 60), 2)
        opened = now - timedelta(minutes=rng.randint(5, 60 * 24 * 30))
        duration_min = rng.randint(2, 360)
        closed = opened + timedelta(minutes=duration_min)
        price_open = round(rng.uniform(0.5, 2.0) if "USD" in sym and sym != "XAUUSD" else rng.uniform(1000, 70000), 4)
        price_close = round(price_open * (1 + rng.gauss(0, 0.002)), 4)
        trades.append({
            "id": f"{account_id}-T{i:05d}",
            "symbol": sym,
            "side": side,
            "lots": lots,
            "pnl": pnl,
            "open_time": opened.isoformat(),
            "close_time": closed.isoformat(),
            "open_price": price_open,
            "close_price": price_close,
            "strategy": rng.choice(STRATEGIES),
            "duration_min": duration_min,
        })
    trades.sort(key=lambda x: x["close_time"], reverse=True)
    return trades


def _build_account(idx: int):
    rng = random.Random(100 + idx)
    login = 5000000 + rng.randint(0, 999999)
    balance = round(rng.uniform(10000, 250000), 2)
    leverage = rng.choice([30, 100, 200, 500])
    series = _gen_equity_series(balance, days=90, vol=rng.uniform(0.005, 0.012),
                                drift=rng.uniform(-0.0002, 0.0014), seed=200 + idx)
    last_equity = series[-1]["equity"]
    daily_pnl = round(last_equity - series[-5]["equity"], 2)
    dd_series, max_dd = _drawdown_from_equity(series)
    # current dd
    peak = max(p["equity"] for p in series)
    current_dd = round((last_equity - peak) / peak * 100.0, 2) if peak > 0 else 0.0
    status = rng.choice(["LIVE", "LIVE", "LIVE", "PAUSED", "ERROR"])
    open_positions = rng.randint(0, 14)
    margin_used = round(last_equity * rng.uniform(0.05, 0.45), 2)
    margin_level = round((last_equity / max(margin_used, 1)) * 100, 1)
    return {
        "id": f"ACC-{idx:03d}",
        "login": login,
        "broker": rng.choice(BROKERS),
        "strategy": rng.choice(STRATEGIES),
        "currency": "USD",
        "leverage": leverage,
        "balance": balance,
        "equity": round(last_equity, 2),
        "daily_pnl": daily_pnl,
        "max_drawdown": max_dd,
        "current_drawdown": current_dd,
        "open_positions": open_positions,
        "margin_used": margin_used,
        "margin_level": margin_level,
        "status": status,
        "kill_switch": False,
        "risk_limits": {
            "max_daily_loss_pct": rng.choice([2.0, 3.0, 5.0]),
            "max_position_size_lots": rng.choice([1.0, 2.0, 5.0]),
            "max_open_positions": rng.choice([10, 20, 50]),
        },
        "_equity_series": series,
        "_drawdown_series": dd_series,
        "_trades": _gen_trades(f"ACC-{idx:03d}", n=140, seed=300 + idx),
    }


ACCOUNTS = [_build_account(i) for i in range(1, 9)]


def _build_alerts():
    now = datetime.now(timezone.utc)
    samples = [
        ("CRITICAL", "ACC-003", "Max daily loss reached (-3.2%). EA paused automatically.", 4),
        ("WARNING", "ACC-001", "Drawdown -4.8% approaching limit (-5%).", 18),
        ("WARNING", "ACC-005", "Slippage spike on XAUUSD (avg 2.4 pips).", 32),
        ("INFO", "ACC-002", "EA 'Trend Follow Alpha' deployed v2.1.4.", 55),
        ("CRITICAL", "ACC-007", "Connection lost to broker for 42s. Reconnected.", 71),
        ("INFO", "ACC-004", "Weekly performance report generated.", 90),
        ("WARNING", "ACC-006", "Margin level dropped below 250%.", 110),
        ("INFO", "ACC-008", "New trade cluster opened (5 positions, EURUSD).", 140),
        ("WARNING", "ACC-001", "Latency to broker > 180ms (avg 60ms).", 175),
        ("INFO", "ACC-002", "Daily P&L crossed +1.5% threshold.", 210),
    ]
    return [
        {
            "id": f"ALT-{i:04d}",
            "severity": sev,
            "account_id": acc,
            "message": msg,
            "timestamp": (now - timedelta(minutes=mins)).isoformat(),
            "acknowledged": False,
        }
        for i, (sev, acc, msg, mins) in enumerate(samples)
    ]


ALERTS = _build_alerts()


# ------------------------------------------------------------
# Models
# ------------------------------------------------------------
class KillSwitchPayload(BaseModel):
    enabled: bool


class RiskLimitsPayload(BaseModel):
    max_daily_loss_pct: Optional[float] = None
    max_position_size_lots: Optional[float] = None
    max_open_positions: Optional[int] = None


class AckAlertPayload(BaseModel):
    acknowledged: bool = True


class AtlasReportIn(BaseModel):
    supervisor: str = "Sr. Atlas"
    ecosystem: str = "Forge Factory Lab"
    status: Optional[str] = None
    backend_ok: Optional[bool] = None
    bridge_ok: Optional[bool] = None
    dashboard_ok: Optional[bool] = None
    message: Optional[str] = None
    source: str = "manual"
    metrics: Optional[dict] = None
    account_id: Optional[str] = None  # when set, only that account is snapshotted


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _account_public(acc: dict) -> dict:
    return {k: v for k, v in acc.items() if not k.startswith("_")}


def _find_account(account_id: str) -> dict:
    for a in ACCOUNTS:
        if a["id"] == account_id:
            return a
    raise HTTPException(status_code=404, detail="Account not found")


# ------------------------------------------------------------
# Phase 2 — Sr. Atlas supervision snapshot.
# Aggregates KPIs, account health, risk and alerts into a single
# supervisor-oriented view with an overall OK / WARNING / ALERT status.
# ------------------------------------------------------------
def _supervision_snapshot_from_accounts(
    accounts: list[dict],
    *,
    bridge_ok: bool | None = None,
    alerts: list[dict] | None = None,
) -> dict:
    alert_rows = ALERTS if alerts is None else alerts
    total_equity = sum(a.get("equity", 0.0) for a in accounts)
    total_balance = sum(a.get("balance", 0.0) for a in accounts)
    daily_pnl = sum(a.get("daily_pnl", 0.0) for a in accounts)
    open_positions = sum(a.get("open_positions", 0) for a in accounts)

    live = sum(1 for a in accounts if a.get("status") == "LIVE")
    paused = sum(1 for a in accounts if a.get("status") == "PAUSED")
    error = sum(1 for a in accounts if a.get("status") == "ERROR")

    active_alerts = sum(1 for a in alert_rows if not a.get("acknowledged"))
    critical = sum(1 for a in alert_rows if a.get("severity") == "CRITICAL" and not a.get("acknowledged"))
    warning = sum(1 for a in alert_rows if a.get("severity") == "WARNING" and not a.get("acknowledged"))

    n = max(len(accounts), 1)
    avg_dd = round(sum(float(a.get("current_drawdown", 0.0)) for a in accounts) / n, 2) if accounts else 0.0
    worst_dd = round(min((float(a.get("current_drawdown", 0.0)) for a in accounts), default=0.0), 2)
    accounts_over_limit = sum(
        1 for a in accounts
        if abs(float(a.get("current_drawdown", 0.0)))
        >= float((a.get("risk_limits") or {}).get("max_daily_loss_pct", 5.0))
    )

    # Account/alert severity first — ALERT must keep priority over bridge failure.
    if error > 0 or critical > 0:
        status = "ALERT"
    elif paused > 0 or warning > 0 or accounts_over_limit > 0:
        status = "WARNING"
    else:
        status = "OK"

    bridge_down = bridge_ok is False
    # Historical real cache is not mock; still never report OK while the bridge is down.
    if bridge_down and status == "OK":
        status = "WARNING"

    services = {
        "backend_ok": True,
        "store_ok": True,
        "bridge_ok": bridge_ok if bridge_ok is not None else (True if MT5_MODE else None),
        "dashboard_ok": True,
    }

    if bridge_down:
        if accounts:
            cache_note = (
                "MT5 bridge is unavailable; displayed data comes from cache "
                "and may be outdated."
            )
        else:
            cache_note = (
                "MT5 bridge is unavailable and no cached account data is available."
            )
        if status == "ALERT":
            message = (
                f"ALERT: {critical} critical alert(s), {error} account(s) in ERROR state. "
                f"{cache_note}"
            )
        elif paused > 0 or warning > 0 or accounts_over_limit > 0:
            message = (
                f"Degraded: {warning} warning alert(s), {paused} paused account(s), "
                f"{accounts_over_limit} account(s) near risk limits. {cache_note}"
            )
        else:
            message = cache_note
    elif not accounts and MT5_MODE:
        if status == "OK":
            status = "WARNING"
        message = (
            "MT5 mode is active but no live account data is available from the bridge yet."
        )
    elif status == "OK":
        message = "All Forge Factory Lab core services are online and healthy."
    elif status == "WARNING":
        message = (
            f"Degraded: {warning} warning alert(s), {paused} paused account(s), "
            f"{accounts_over_limit} account(s) near risk limits."
        )
    else:
        message = f"ALERT: {critical} critical alert(s), {error} account(s) in ERROR state."

    return {
        "supervisor": "Sr. Atlas",
        "ecosystem": "Forge Factory Lab",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mt5" if MT5_MODE else "mock",
        "status": status,
        "kpis": {
            "total_equity": round(total_equity, 2),
            "total_balance": round(total_balance, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl / total_equity * 100, 2) if total_equity else 0.0,
            "open_positions": open_positions,
        },
        "accounts": {"total": len(accounts), "live": live, "paused": paused, "error": error},
        "risk": {
            "avg_drawdown": avg_dd,
            "worst_drawdown": worst_dd,
            "accounts_over_limit": accounts_over_limit,
        },
        "alerts": {"active": active_alerts, "critical": critical, "warning": warning},
        "services": services,
        "message": message,
    }


def _supervision_snapshot() -> dict:
    """Mock-mode snapshot (sync). Prefer `_live_supervision_snapshot` when serving HTTP."""
    return _supervision_snapshot_from_accounts(ACCOUNTS, bridge_ok=None)


async def _mt5_live_accounts() -> tuple[list[dict], bool]:
    """Fetch enriched accounts from configured MT5 bridge(s). Returns (accounts, bridge_ok)."""
    import httpx
    from mt5_adapter import account_from_bridge, drawdown_from_equity
    from mt5_client import clients

    out: list[dict] = []
    any_reachable = False
    for client in clients():
        try:
            bridge_acc = await client.account()
        except (httpx.HTTPError, httpx.HTTPStatusError) as e:
            logging.getLogger("server").warning(
                "bridge %s account fetch failed: %s", client.endpoint.url, e
            )
            continue
        if not bridge_acc:
            continue
        any_reachable = True
        try:
            positions = await client.positions()
        except httpx.HTTPError:
            positions = []
        login = int(bridge_acc["login"])
        if _cache is not None:
            overrides = await _cache.get_overrides(login)
            anchor = await _cache.maybe_set_daily_anchor(
                login, bridge_acc.get("balance", 0.0)
            )
            eq_doc = await _cache.get(f"equity:{login}")
            series = (eq_doc or {}).get("payload", {}).get("series", []) or []
        else:
            overrides = {
                "risk_limits": {
                    "max_daily_loss_pct": 5.0,
                    "max_position_size_lots": 1.0,
                    "max_open_positions": 10,
                },
                "kill_switch": False,
            }
            anchor = None
            series = []
        _, max_dd, current_dd = drawdown_from_equity(series)
        acc = account_from_bridge(
            bridge_acc,
            positions_count=len(positions),
            risk_limits=overrides["risk_limits"],
            kill_switch=overrides["kill_switch"],
            max_dd=max_dd,
            current_dd=current_dd,
            daily_pnl_anchor=anchor,
        )
        # Keep raw positions for per-account report enrichment (Part 3).
        # Leading underscore: not part of the public account API contract.
        acc["_positions"] = positions
        if _cache is not None:
            await _cache.put(f"account:{login}", {k: v for k, v in acc.items() if not k.startswith("_")})
            await _cache.put(f"positions:{login}", positions)
        out.append(acc)

    if not any_reachable and _cache is not None:
        # Fall back to cached account snapshots (same strategy as routes_mt5).
        try:
            cached_keys = await _cache.cache.find(
                {"_id": {"$regex": r"^account:"}}, {"_id": 0}
            ).to_list(50)
            for d in cached_keys:
                payload = d.get("payload")
                if payload:
                    payload = dict(payload)
                    payload["stale"] = True
                    out.append(payload)
        except Exception as e:  # noqa: BLE001
            logging.getLogger("server").warning("cache account fallback failed: %s", e)

    return out, any_reachable


async def _live_supervision_snapshot() -> dict:
    if not MT5_MODE:
        return _supervision_snapshot()
    accounts, bridge_ok = await _mt5_live_accounts()
    # Do not mix mock ALERTS into live MT5 supervision — that would be untruthful.
    return _supervision_snapshot_from_accounts(
        accounts, bridge_ok=bridge_ok, alerts=[]
    )


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"service": "MT5 Quant Supervision API", "status": "ok"}


@api_router.get("/kpis")
async def get_kpis():
    total_equity = sum(a["equity"] for a in ACCOUNTS)
    total_balance = sum(a["balance"] for a in ACCOUNTS)
    daily_pnl = sum(a["daily_pnl"] for a in ACCOUNTS)
    open_positions = sum(a["open_positions"] for a in ACCOUNTS)
    active_alerts = sum(1 for a in ALERTS if not a["acknowledged"])
    critical_alerts = sum(1 for a in ALERTS if a["severity"] == "CRITICAL" and not a["acknowledged"])
    live_accounts = sum(1 for a in ACCOUNTS if a["status"] == "LIVE")
    avg_dd = round(sum(a["current_drawdown"] for a in ACCOUNTS) / max(len(ACCOUNTS), 1), 2)
    return {
        "total_equity": round(total_equity, 2),
        "total_balance": round(total_balance, 2),
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl / total_equity * 100, 2) if total_equity else 0.0,
        "open_positions": open_positions,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "accounts_total": len(ACCOUNTS),
        "accounts_live": live_accounts,
        "avg_drawdown": avg_dd,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@api_router.get("/accounts")
async def list_accounts():
    return [_account_public(a) for a in ACCOUNTS]


@api_router.get("/accounts/{account_id}")
async def get_account(account_id: str):
    acc = _find_account(account_id)
    return _account_public(acc)


@api_router.get("/accounts/{account_id}/equity")
async def get_equity_curve(account_id: str, points: int = 200):
    acc = _find_account(account_id)
    series = acc["_equity_series"]
    if points and len(series) > points:
        step = max(1, len(series) // points)
        series = series[::step]
    return {"account_id": account_id, "series": series}


@api_router.get("/accounts/{account_id}/drawdown")
async def get_drawdown(account_id: str, points: int = 200):
    acc = _find_account(account_id)
    series = acc["_drawdown_series"]
    if points and len(series) > points:
        step = max(1, len(series) // points)
        series = series[::step]
    return {
        "account_id": account_id,
        "series": series,
        "max_drawdown": acc["max_drawdown"],
        "current_drawdown": acc["current_drawdown"],
    }


@api_router.get("/accounts/{account_id}/trades")
async def get_trades(
    account_id: str,
    limit: int = 50,
    symbol: Optional[str] = None,
    side: Optional[Literal["BUY", "SELL"]] = None,
):
    acc = _find_account(account_id)
    trades = acc["_trades"]
    if symbol:
        trades = [t for t in trades if t["symbol"] == symbol]
    if side:
        trades = [t for t in trades if t["side"] == side]
    return {"account_id": account_id, "count": len(trades), "trades": trades[:limit]}


@api_router.post("/accounts/{account_id}/kill-switch")
async def set_kill_switch(account_id: str, payload: KillSwitchPayload):
    acc = _find_account(account_id)
    acc["kill_switch"] = payload.enabled
    acc["status"] = "PAUSED" if payload.enabled else "LIVE"
    return {"account_id": account_id, "kill_switch": acc["kill_switch"], "status": acc["status"]}


@api_router.put("/accounts/{account_id}/risk-limits")
async def update_risk_limits(account_id: str, payload: RiskLimitsPayload):
    acc = _find_account(account_id)
    for k, v in payload.model_dump(exclude_none=True).items():
        acc["risk_limits"][k] = v
    return {"account_id": account_id, "risk_limits": acc["risk_limits"]}


@api_router.get("/alerts")
async def list_alerts(severity: Optional[str] = None, unacknowledged_only: bool = False):
    items = ALERTS
    if severity:
        items = [a for a in items if a["severity"] == severity.upper()]
    if unacknowledged_only:
        items = [a for a in items if not a["acknowledged"]]
    return {"count": len(items), "alerts": items}


@api_router.post("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: str, payload: AckAlertPayload):
    for a in ALERTS:
        if a["id"] == alert_id:
            a["acknowledged"] = payload.acknowledged
            return a
    raise HTTPException(status_code=404, detail="Alert not found")


@api_router.post("/sim/tick")
async def tick():
    """Advance simulated equity/PnL by a small step (for live feel)."""
    rng = random.Random()
    for acc in ACCOUNTS:
        if acc["status"] == "PAUSED":
            continue
        shock = rng.gauss(0.0005, 0.004)
        new_eq = max(1000.0, acc["equity"] * (1 + shock))
        delta = new_eq - acc["equity"]
        acc["equity"] = round(new_eq, 2)
        acc["daily_pnl"] = round(acc["daily_pnl"] + delta, 2)
        # append a tick to series
        acc["_equity_series"].append({
            "t": datetime.now(timezone.utc).isoformat(),
            "equity": acc["equity"],
        })
        if len(acc["_equity_series"]) > 800:
            acc["_equity_series"] = acc["_equity_series"][-800:]
        acc["_drawdown_series"], acc["max_drawdown"] = _drawdown_from_equity(acc["_equity_series"])
        peak = max(p["equity"] for p in acc["_equity_series"])
        acc["current_drawdown"] = round((acc["equity"] - peak) / peak * 100.0, 2) if peak else 0.0
    return {"ok": True, "server_time": datetime.now(timezone.utc).isoformat()}


if MT5_MODE:
    from routes_mt5 import build_router as build_mt5_router
    if ATLAS_STORE == "sqlite":
        from mt5_cache_sqlite import MT5CacheSQLite as MT5Cache
        _cache = MT5Cache(os.environ.get("ATLAS_SQLITE_PATH", str(ROOT_DIR / "data" / "atlas.db")))
    else:
        from mt5_cache import MT5Cache
        _cache = MT5Cache(mongo_db)
    app.include_router(build_mt5_router(_cache))
    logging.getLogger("server").info("MT5 mode ENABLED — store=%s", ATLAS_STORE)
else:
    app.include_router(api_router)
    _cache = None
    logging.getLogger("server").info("MT5 mode disabled — serving MOCK data (set MT5_BRIDGE_URL to switch)")


# ------------------------------------------------------------
# /api/system/health — used by the health-check page (Windows installer)
# ------------------------------------------------------------
@app.get("/api/system/health")
async def system_health():
    import httpx
    out = {
        "mode": "mt5" if MT5_MODE else "mock",
        "version": BUILD_INFO["version"],
        "build": BUILD_INFO,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "store": {"backend": ATLAS_STORE, "ok": True},
        "bridge": None,
    }
    if _cache is not None:
        try:
            await _cache.get("__health_probe__")
        except Exception as e:  # noqa: BLE001
            out["store"]["ok"] = False
            out["store"]["error"] = str(e)
    if MT5_MODE:
        from mt5_client import clients
        bridges = clients()
        if bridges:
            client = bridges[0]
            info = {"url": client.endpoint.url, "reachable": False}
            try:
                h = await client.health()
                info.update({
                    "reachable": True,
                    "terminal_connected": h.get("terminal_connected"),
                    "account_logged_in": h.get("account_logged_in"),
                    "login": h.get("login"),
                    "server": h.get("server"),
                    "last_error": h.get("last_error"),
                    "trade_allowed": h.get("trade_allowed"),
                    "message": h.get("message"),
                })
            except (httpx.HTTPError, Exception) as e:  # noqa: BLE001
                info["error"] = str(e)
            out["bridge"] = info
    return out


# ------------------------------------------------------------
# /api/system/version — lightweight endpoint the Dashboard uses
# to display the exact running build/version.
# ------------------------------------------------------------
@app.get("/api/system/version")
async def system_version():
    return BUILD_INFO


# ------------------------------------------------------------
# MT5 connection configuration — managed from the Dashboard.
# (Replaces the one-time install wizard: credentials can now be
#  set and changed at any time without reinstalling Atlas.)
# ------------------------------------------------------------
import mt5_config as _mt5cfg


class MT5ConfigIn(BaseModel):
    login: str
    password: Optional[str] = ""
    server: str
    terminal_path: Optional[str] = ""
    bridge_host: Optional[str] = "127.0.0.1"
    bridge_port: Optional[int] = 8002


def _connection_status(cfg: dict) -> dict:
    configured = bool(cfg.get("configured"))
    if MT5_MODE:
        state = "connected"        # backend started with a bridge URL
    elif configured:
        state = "pending_restart"  # saved; waiting for services to pick it up
    else:
        state = "unconfigured"     # Configuration Mode
    return {
        "mode": "mt5" if MT5_MODE else "mock",
        "configured": configured,
        "state": state,
        "platform": "windows" if os.name == "nt" else "preview",
        "server": cfg.get("server") or None,
        "login": cfg.get("login") or None,
        "bridge_port": cfg.get("bridge_port"),
        "updated_at": cfg.get("updated_at"),
    }


@app.get("/api/mt5/config")
async def get_mt5_config():
    cfg = _mt5cfg.load()
    return {"config": _mt5cfg.masked(cfg), "status": _connection_status(cfg)}


@app.put("/api/mt5/config")
async def put_mt5_config(payload: MT5ConfigIn):
    try:
        cfg = _mt5cfg.save_config(payload.model_dump())
    except _mt5cfg.ConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))
    applied = _mt5cfg.apply_to_windows(cfg)
    return {
        "saved": True,
        "applied": applied,
        "restart_required": (not MT5_MODE),
        "config": _mt5cfg.masked(cfg),
        "status": _connection_status(cfg),
        "message": (
            "MT5 settings saved. Atlas is applying them and the services are "
            "restarting — the dashboard will reconnect shortly."
        ) if applied else (
            "MT5 settings saved. On the Windows installation Atlas will restart "
            "its services and connect automatically. In this preview the backend "
            "stays in mock mode."
        ),
    }


@app.delete("/api/mt5/config")
async def delete_mt5_config():
    cfg = _mt5cfg.clear_config()
    return {"cleared": True, "config": _mt5cfg.masked(cfg), "status": _connection_status(cfg)}


# ------------------------------------------------------------
# Phase 2 — Sr. Atlas supervision endpoints (mounted on `app` so they
# are available in both mock and MT5 modes, like /api/system/health).
# ------------------------------------------------------------
@app.get("/api/supervision/snapshot")
async def supervision_snapshot():
    return await _live_supervision_snapshot()


def _account_report_status(acc: dict, *, bridge_ok: bool | None) -> str:
    return account_report_status(acc, bridge_ok=bridge_ok)


def _build_account_report(
    acc: dict,
    *,
    source: str,
    bridge_ok: bool | None,
    supervisor: str = "Sr. Atlas",
    ecosystem: str = "Forge Factory Lab",
    message_override: str | None = None,
    status_override: str | None = None,
    backend_ok: bool | None = None,
    dashboard_ok: bool | None = None,
    positions: list | None = None,
    deals: list | None = None,
    previous_report: dict | None = None,
    label_overrides: dict | None = None,
) -> dict:
    return build_account_report(
        acc,
        source=source,
        bridge_ok=bridge_ok,
        supervisor=supervisor,
        ecosystem=ecosystem,
        message_override=message_override,
        status_override=status_override,
        backend_ok=backend_ok,
        dashboard_ok=dashboard_ok,
        positions=positions,
        deals=deals,
        previous_report=previous_report,
        label_overrides=label_overrides,
    )


async def _accounts_for_reports() -> tuple[list[dict], bool | None]:
    """Accounts to snapshot + bridge_ok flag (None in mock mode)."""
    if not MT5_MODE:
        # Full mock accounts (incl. _trades) — builder only emits safe fields.
        return list(ACCOUNTS), None
    accounts, bridge_ok = await _mt5_live_accounts()
    return accounts, bridge_ok


async def _deals_and_labels_for_account(acc: dict) -> tuple[list[dict], dict[int, str]]:
    """Fetch deals + EA label overrides for one account (live or cache)."""
    import httpx
    from mt5_client import clients

    login = int(acc.get("login") or 0)
    labels: dict[int, str] = {}
    if _cache is not None:
        try:
            labels = await _cache.get_ea_labels(login)
        except Exception as e:  # noqa: BLE001
            logging.getLogger("server").warning("ea labels load failed: %s", e)

    if not MT5_MODE:
        return [], labels

    for client in clients():
        try:
            bridge_acc = await client.account()
        except (httpx.HTTPError, httpx.HTTPStatusError):
            continue
        if not bridge_acc or int(bridge_acc.get("login") or 0) != login:
            continue
        try:
            deals = await client.deals(days=90)
            if _cache is not None:
                await _cache.put(f"deals:{login}", deals)
            return list(deals or []), labels
        except httpx.HTTPError as e:
            logging.getLogger("server").warning(
                "deals fetch failed for login %s: %s", login, e
            )
            break

    if _cache is not None:
        cached = await _cache.get(f"deals:{login}")
        if cached and cached.get("payload") is not None:
            return list(cached["payload"]), labels
    return [], labels


async def _positions_for_account(acc: dict) -> list[dict]:
    """Prefer positions attached during live fetch; else cache; else empty."""
    attached = acc.get("_positions")
    if isinstance(attached, list):
        return attached
    if not MT5_MODE or _cache is None:
        return []
    login = int(acc.get("login") or 0)
    cached = await _cache.get(f"positions:{login}")
    if cached and cached.get("payload") is not None:
        return list(cached["payload"])
    return []


async def _capture_snapshot_reports(
    source: str = "auto",
    *,
    account_id: str | None = None,
    message_override: str | None = None,
    status_override: str | None = None,
    backend_ok: bool | None = None,
    dashboard_ok: bool | None = None,
    bridge_ok_override: bool | None = None,
    supervisor: str = "Sr. Atlas",
    ecosystem: str = "Forge Factory Lab",
    metrics_override: dict | None = None,
) -> list[dict]:
    """Persist one enriched report per configured/reachable account."""
    accounts, bridge_ok = await _accounts_for_reports()
    if bridge_ok_override is not None:
        bridge_ok = bridge_ok_override
    if account_id:
        accounts = [a for a in accounts if a.get("id") == account_id]
        if not accounts:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    stored: list[dict] = []
    for acc in accounts:
        previous = await _atlas_store.latest_for_account(acc["id"])
        positions = await _positions_for_account(acc)
        deals, labels = await _deals_and_labels_for_account(acc)
        report = _build_account_report(
            acc,
            source=source,
            bridge_ok=bridge_ok,
            supervisor=supervisor,
            ecosystem=ecosystem,
            message_override=message_override,
            status_override=status_override,
            backend_ok=backend_ok,
            dashboard_ok=dashboard_ok,
            positions=positions if (positions or MT5_MODE) else None,
            deals=deals if MT5_MODE else None,
            previous_report=previous,
            label_overrides=labels,
        )
        if metrics_override is not None and account_id:
            report["metrics"] = metrics_override
        stored.append(await _atlas_store.add(report))
    return stored


@app.post("/api/atlas/report")
async def create_atlas_report(payload: AtlasReportIn):
    """Generate and persist one report per account (or a single account_id)."""
    reports = await _capture_snapshot_reports(
        source=payload.source or "manual",
        account_id=payload.account_id,
        message_override=payload.message,
        status_override=payload.status,
        backend_ok=payload.backend_ok,
        dashboard_ok=payload.dashboard_ok,
        bridge_ok_override=payload.bridge_ok,
        supervisor=payload.supervisor,
        ecosystem=payload.ecosystem,
        metrics_override=payload.metrics,
    )
    return {"count": len(reports), "reports": reports}


@app.get("/api/atlas/reports")
async def list_atlas_reports(
    limit: int = 50,
    status: Optional[str] = None,
    account_id: Optional[str] = None,
):
    reports = await _atlas_store.list(
        limit=limit, status=status, account_id=account_id
    )
    total = await _atlas_store.count(status=status, account_id=account_id)
    return {"count": len(reports), "total": total, "reports": reports}


# ------------------------------------------------------------
# Phase 2 — automatic per-account supervision snapshot support.
# ------------------------------------------------------------
async def _capture_snapshot_report(source: str = "auto") -> dict:
    """Backward-compatible wrapper: returns first report + full list meta."""
    reports = await _capture_snapshot_reports(source=source)
    if not reports:
        return {
            "count": 0,
            "reports": [],
            "source": source,
            "message": "No accounts available to snapshot.",
        }
    # Keep previous single-object shape fields for older clients, plus list.
    first = dict(reports[0])
    first["count"] = len(reports)
    first["reports"] = reports
    return first


@app.get("/api/supervision/config")
async def supervision_config():
    return {
        "auto_snapshot_enabled": AUTO_SNAPSHOT_INTERVAL_SEC > 0,
        "interval_sec": AUTO_SNAPSHOT_INTERVAL_SEC,
        "retention_days": REPORT_RETENTION_DAYS,
        "store_backend": _atlas_store.backend,
        "mode": "mt5" if MT5_MODE else "mock",
    }


@app.post("/api/supervision/auto-snapshot")
async def trigger_auto_snapshot():
    """On-demand automatic snapshot capture (source='auto'), one report per account."""
    return await _capture_snapshot_report(source="auto")


async def _purge_old_reports_loop():
    """Background retention purge — never blocks startup."""
    log = logging.getLogger("server")
    # Small delay so uvicorn finishes boot before first purge.
    await asyncio.sleep(2)
    try:
        deleted = await _atlas_store.purge_older_than(REPORT_RETENTION_DAYS)
        if deleted:
            log.info(
                "Purged %s atlas report(s) older than %s day(s)",
                deleted,
                REPORT_RETENTION_DAYS,
            )
    except Exception as e:  # noqa: BLE001
        log.warning("Initial report retention purge failed: %s", e)

    while True:
        try:
            # Re-check roughly once a day (also after each auto-snapshot interval
            # when that is longer — but keep a sane upper bound).
            await asyncio.sleep(max(3600, AUTO_SNAPSHOT_INTERVAL_SEC or 3600))
            deleted = await _atlas_store.purge_older_than(REPORT_RETENTION_DAYS)
            if deleted:
                log.info(
                    "Purged %s atlas report(s) older than %s day(s)",
                    deleted,
                    REPORT_RETENTION_DAYS,
                )
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001
            log.warning("Report retention purge failed: %s", e)


async def _auto_snapshot_loop():
    logging.getLogger("server").info(
        "Auto-snapshot scheduler ENABLED — every %ss (per account)",
        AUTO_SNAPSHOT_INTERVAL_SEC,
    )
    while True:
        try:
            await asyncio.sleep(AUTO_SNAPSHOT_INTERVAL_SEC)
            await _capture_snapshot_reports(source="auto")
            try:
                await _atlas_store.purge_older_than(REPORT_RETENTION_DAYS)
            except Exception as pe:  # noqa: BLE001
                logging.getLogger("server").warning(
                    "Post-snapshot retention purge failed: %s", pe
                )
        except asyncio.CancelledError:  # graceful shutdown
            break
        except Exception as e:  # noqa: BLE001
            logging.getLogger("server").warning("Auto-snapshot failed: %s", e)


@app.on_event("startup")
async def _start_auto_snapshot():
    app.state.report_purge_task = asyncio.create_task(_purge_old_reports_loop())
    if AUTO_SNAPSHOT_INTERVAL_SEC > 0:
        app.state.auto_snapshot_task = asyncio.create_task(_auto_snapshot_loop())


@app.on_event("shutdown")
async def _stop_auto_snapshot():
    for name in ("auto_snapshot_task", "report_purge_task"):
        task = getattr(app.state, name, None)
        if task:
            task.cancel()


# ------------------------------------------------------------
# /healthcheck — standalone HTML page (works without dashboard)
# ------------------------------------------------------------
@app.get("/healthcheck")
async def healthcheck_page():
    return FileResponse(ROOT_DIR / "healthcheck.html")


# ------------------------------------------------------------
# Static frontend serving (Windows installer mode).
# Set SERVE_FRONTEND=true and FRONTEND_BUILD=/path/to/build to enable.
# Must be mounted LAST so /api/* routes take precedence.
# ------------------------------------------------------------
if os.environ.get("SERVE_FRONTEND", "false").lower() == "true":
    from fastapi.staticfiles import StaticFiles
    fb = Path(os.environ.get("FRONTEND_BUILD", str(ROOT_DIR / ".." / "frontend_build")))
    if (fb / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(fb), html=True), name="frontend")
        logging.getLogger("server").info("Serving frontend from %s", fb)
    else:
        logging.getLogger("server").warning("SERVE_FRONTEND=true but %s/index.html missing", fb)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

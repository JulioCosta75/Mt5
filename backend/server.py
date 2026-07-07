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
# When > 0, a background task persists a supervision report (source="auto")
# every N seconds. Default 0 (disabled) so the preview DB stays clean; the
# capability is always available on-demand via POST /api/supervision/auto-snapshot.
try:
    AUTO_SNAPSHOT_INTERVAL_SEC = int(os.environ.get("ATLAS_AUTO_SNAPSHOT_INTERVAL_SEC", "0"))
except ValueError:
    AUTO_SNAPSHOT_INTERVAL_SEC = 0

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
# Uses Mongo when available (preview/Linux), in-memory otherwise.
# ------------------------------------------------------------
from atlas_store import AtlasReportStore
_atlas_store = AtlasReportStore(mongo_db)

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
def _supervision_snapshot() -> dict:
    total_equity = sum(a["equity"] for a in ACCOUNTS)
    total_balance = sum(a["balance"] for a in ACCOUNTS)
    daily_pnl = sum(a["daily_pnl"] for a in ACCOUNTS)
    open_positions = sum(a["open_positions"] for a in ACCOUNTS)

    live = sum(1 for a in ACCOUNTS if a["status"] == "LIVE")
    paused = sum(1 for a in ACCOUNTS if a["status"] == "PAUSED")
    error = sum(1 for a in ACCOUNTS if a["status"] == "ERROR")

    active_alerts = sum(1 for a in ALERTS if not a["acknowledged"])
    critical = sum(1 for a in ALERTS if a["severity"] == "CRITICAL" and not a["acknowledged"])
    warning = sum(1 for a in ALERTS if a["severity"] == "WARNING" and not a["acknowledged"])

    n = max(len(ACCOUNTS), 1)
    avg_dd = round(sum(a["current_drawdown"] for a in ACCOUNTS) / n, 2)
    worst_dd = round(min((a["current_drawdown"] for a in ACCOUNTS), default=0.0), 2)
    accounts_over_limit = sum(
        1 for a in ACCOUNTS
        if abs(a["current_drawdown"]) >= float(a["risk_limits"]["max_daily_loss_pct"])
    )

    if error > 0 or critical > 0:
        status = "ALERT"
    elif paused > 0 or warning > 0 or accounts_over_limit > 0:
        status = "WARNING"
    else:
        status = "OK"

    services = {
        "backend_ok": True,
        "store_ok": True,
        "bridge_ok": True if MT5_MODE else None,
        "dashboard_ok": True,
    }

    if status == "OK":
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
        "accounts": {"total": len(ACCOUNTS), "live": live, "paused": paused, "error": error},
        "risk": {
            "avg_drawdown": avg_dd,
            "worst_drawdown": worst_dd,
            "accounts_over_limit": accounts_over_limit,
        },
        "alerts": {"active": active_alerts, "critical": critical, "warning": warning},
        "services": services,
        "message": message,
    }


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
                })
            except (httpx.HTTPError, Exception) as e:  # noqa: BLE001
                info["error"] = str(e)
    return out


# ------------------------------------------------------------
# /api/system/version — lightweight endpoint the Dashboard uses
# to display the exact running build/version.
# ------------------------------------------------------------
@app.get("/api/system/version")
async def system_version():
    return BUILD_INFO


# ------------------------------------------------------------
# Phase 2 — Sr. Atlas supervision endpoints (mounted on `app` so they
# are available in both mock and MT5 modes, like /api/system/health).
# ------------------------------------------------------------
@app.get("/api/supervision/snapshot")
async def supervision_snapshot():
    return _supervision_snapshot()


@app.post("/api/atlas/report")
async def create_atlas_report(payload: AtlasReportIn):
    snap = _supervision_snapshot()
    report = {
        "supervisor": payload.supervisor,
        "ecosystem": payload.ecosystem,
        "status": (payload.status or snap["status"]).upper(),
        "backend_ok": payload.backend_ok if payload.backend_ok is not None else snap["services"]["backend_ok"],
        "bridge_ok": payload.bridge_ok if payload.bridge_ok is not None else snap["services"]["bridge_ok"],
        "dashboard_ok": payload.dashboard_ok if payload.dashboard_ok is not None else snap["services"]["dashboard_ok"],
        "message": payload.message or snap["message"],
        "source": payload.source,
        "metrics": payload.metrics or {
            "total_equity": snap["kpis"]["total_equity"],
            "daily_pnl": snap["kpis"]["daily_pnl"],
            "accounts_live": snap["accounts"]["live"],
            "active_alerts": snap["alerts"]["active"],
            "critical_alerts": snap["alerts"]["critical"],
            "avg_drawdown": snap["risk"]["avg_drawdown"],
        },
    }
    stored = await _atlas_store.add(report)
    return stored


@app.get("/api/atlas/reports")
async def list_atlas_reports(limit: int = 50, status: Optional[str] = None):
    reports = await _atlas_store.list(limit=limit, status=status)
    total = await _atlas_store.count()
    return {"count": len(reports), "total": total, "reports": reports}


# ------------------------------------------------------------
# Phase 2 — automatic supervision snapshot support.
# Captures the live snapshot and persists it as a report. Reused by the
# background scheduler and the on-demand endpoint below.
# ------------------------------------------------------------
async def _capture_snapshot_report(source: str = "auto") -> dict:
    snap = _supervision_snapshot()
    report = {
        "supervisor": snap["supervisor"],
        "ecosystem": snap["ecosystem"],
        "status": snap["status"],
        "backend_ok": snap["services"]["backend_ok"],
        "bridge_ok": snap["services"]["bridge_ok"],
        "dashboard_ok": snap["services"]["dashboard_ok"],
        "message": snap["message"],
        "source": source,
        "metrics": {
            "total_equity": snap["kpis"]["total_equity"],
            "daily_pnl": snap["kpis"]["daily_pnl"],
            "accounts_live": snap["accounts"]["live"],
            "active_alerts": snap["alerts"]["active"],
            "critical_alerts": snap["alerts"]["critical"],
            "avg_drawdown": snap["risk"]["avg_drawdown"],
        },
    }
    return await _atlas_store.add(report)


@app.get("/api/supervision/config")
async def supervision_config():
    return {
        "auto_snapshot_enabled": AUTO_SNAPSHOT_INTERVAL_SEC > 0,
        "interval_sec": AUTO_SNAPSHOT_INTERVAL_SEC,
        "store_backend": _atlas_store.backend,
        "mode": "mt5" if MT5_MODE else "mock",
    }


@app.post("/api/supervision/auto-snapshot")
async def trigger_auto_snapshot():
    """On-demand automatic snapshot capture (source='auto')."""
    return await _capture_snapshot_report(source="auto")


async def _auto_snapshot_loop():
    logging.getLogger("server").info(
        "Auto-snapshot scheduler ENABLED — every %ss", AUTO_SNAPSHOT_INTERVAL_SEC
    )
    while True:
        try:
            await asyncio.sleep(AUTO_SNAPSHOT_INTERVAL_SEC)
            await _capture_snapshot_report(source="auto")
        except asyncio.CancelledError:  # graceful shutdown
            break
        except Exception as e:  # noqa: BLE001
            logging.getLogger("server").warning("Auto-snapshot failed: %s", e)


@app.on_event("startup")
async def _start_auto_snapshot():
    if AUTO_SNAPSHOT_INTERVAL_SEC > 0:
        app.state.auto_snapshot_task = asyncio.create_task(_auto_snapshot_loop())


@app.on_event("shutdown")
async def _stop_auto_snapshot():
    task = getattr(app.state, "auto_snapshot_task", None)
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

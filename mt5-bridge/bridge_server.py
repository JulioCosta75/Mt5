"""FastAPI server exposing MT5 data over HTTP/JSON.

Runs on a Windows host with the MT5 terminal installed and a logged-in account.
Protected by a static bearer token (BRIDGE_TOKEN env var). Designed to be
consumed by the Linux backend at /app/backend.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from config import Settings
from equity_reconstructor import merge_with_snapshots, reconstruct
from mt5_service import MT5Error, MT5Service, run_sync
from snapshot_recorder import SnapshotRecorder
from storage import Storage

settings = Settings.load()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mt5-bridge")

storage = Storage(settings.sqlite_path)
mt5_service = MT5Service(
    login=settings.mt5_login,
    password=settings.mt5_password,
    server=settings.mt5_server,
    terminal_path=settings.mt5_terminal_path,
)
recorder = SnapshotRecorder(mt5_service, storage, settings.snapshot_interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        mt5_service.initialize()
    except MT5Error as e:
        logger.error("MT5 initialize failed at startup: %s", e)
        # Keep running so /health can report the failure; consumer can decide
    recorder.start()
    yield
    recorder.stop()
    mt5_service.shutdown()


app = FastAPI(title="MT5 Bridge", version="0.1.0", lifespan=lifespan)


def require_token(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.bridge_token:
        raise HTTPException(status_code=403, detail="invalid token")


@app.get("/health")
async def health():
    """Unauthenticated lightweight health check (boolean only)."""
    return await run_sync(mt5_service.health)


@app.get("/account", dependencies=[Depends(require_token)])
async def account():
    try:
        return await run_sync(mt5_service.account_info)
    except MT5Error as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/positions", dependencies=[Depends(require_token)])
async def positions():
    return await run_sync(mt5_service.positions)


@app.get("/orders", dependencies=[Depends(require_token)])
async def orders():
    return await run_sync(mt5_service.orders)


@app.get("/deals", dependencies=[Depends(require_token)])
async def deals(days: int = Query(90, ge=1, le=365)):
    return await run_sync(mt5_service.deals, days)


@app.get("/equity-history", dependencies=[Depends(require_token)])
async def equity_history(days: int = Query(90, ge=1, le=365)):
    info = await run_sync(mt5_service.account_info)
    deals_list = await run_sync(mt5_service.deals, days)
    reconstructed = reconstruct(deals_list, info["balance"])
    storage.upsert_reconstructed(mt5_service.login, reconstructed)
    snapshots = storage.list_snapshots(mt5_service.login, limit=20000)
    merged = merge_with_snapshots(reconstructed, snapshots)
    return {
        "account_login": mt5_service.login,
        "series": merged,
        "reconstructed_points": len(reconstructed),
        "snapshot_points": len(snapshots),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bridge_server:app",
        host=settings.bridge_host,
        port=settings.bridge_port,
        log_level=settings.log_level.lower(),
    )

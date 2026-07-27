"""SQLite-backed equivalent of MT5Cache (the Mongo version).

Provides the **exact same async API** so it can be swapped in via:

    ATLAS_STORE=sqlite
    ATLAS_SQLITE_PATH=C:\\Atlas\\data\\atlas.db

Used by the Windows installer where bundling MongoDB would be heavy.
Single-file persistence, safe for single-process (Atlas Backend service).
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mt5_cache (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mt5_overrides (
    login INTEGER PRIMARY KEY,
    kill_switch INTEGER NOT NULL DEFAULT 0,
    risk_limits TEXT NOT NULL,
    daily_pnl_anchor TEXT
);
"""

_DEFAULT_LIMITS = {
    "max_daily_loss_pct": 3.0,
    "max_position_size_lots": 1.0,
    "max_open_positions": 20,
}


class _Cursor:
    """Tiny async-find-like result wrapper to match Motor's `.to_list()`."""
    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def to_list(self, limit: int = 0) -> list[dict]:
        return self._rows[:limit] if limit else self._rows


class _CollectionShim:
    """Mimics motor `cache.find(...).to_list(N)` used by routes_mt5.list_accounts."""
    def __init__(self, parent: "MT5CacheSQLite"):
        self._parent = parent

    def find(self, query: dict, projection: dict | None = None) -> _Cursor:
        rows = self._parent._find_cache(query)
        return _Cursor(rows)


class MT5CacheSQLite:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._cx() as cx:
            cx.executescript(_SCHEMA)
        self.cache = _CollectionShim(self)  # for routes_mt5 compatibility

    @contextmanager
    def _cx(self):
        cx = sqlite3.connect(self.path, isolation_level=None)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
        finally:
            cx.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ---- internals (sync) ----
    def _put(self, key: str, payload: Any) -> None:
        with self._cx() as cx:
            cx.execute(
                "INSERT INTO mt5_cache (id, payload, fetched_at) VALUES (?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, fetched_at=excluded.fetched_at",
                (key, json.dumps(payload), self._now_iso()),
            )

    def _get(self, key: str) -> dict | None:
        with self._cx() as cx:
            row = cx.execute(
                "SELECT payload, fetched_at FROM mt5_cache WHERE id=?", (key,)
            ).fetchone()
        if not row:
            return None
        return {"payload": json.loads(row["payload"]), "fetched_at": row["fetched_at"]}

    def _find_cache(self, query: dict) -> list[dict]:
        # We support the one shape used: {"_id": {"$regex": r"^account:"}}
        regex = (query or {}).get("_id", {}).get("$regex") if isinstance(query, dict) else None
        with self._cx() as cx:
            if regex:
                like = regex.replace("^", "").replace("$", "") + "%"
                rows = cx.execute(
                    "SELECT id, payload FROM mt5_cache WHERE id LIKE ?", (like,)
                ).fetchall()
            else:
                rows = cx.execute("SELECT id, payload FROM mt5_cache").fetchall()
        return [{"payload": json.loads(r["payload"])} for r in rows]

    def _get_overrides(self, login: int) -> dict:
        with self._cx() as cx:
            row = cx.execute(
                "SELECT kill_switch, risk_limits, daily_pnl_anchor FROM mt5_overrides WHERE login=?",
                (login,),
            ).fetchone()
            if not row:
                cx.execute(
                    "INSERT INTO mt5_overrides (login, kill_switch, risk_limits, daily_pnl_anchor) "
                    "VALUES (?,?,?,?)",
                    (login, 0, json.dumps(_DEFAULT_LIMITS), None),
                )
                return {"kill_switch": False, "risk_limits": dict(_DEFAULT_LIMITS), "daily_pnl_anchor": None}
        return {
            "kill_switch": bool(row["kill_switch"]),
            "risk_limits": json.loads(row["risk_limits"]),
            "daily_pnl_anchor": json.loads(row["daily_pnl_anchor"]) if row["daily_pnl_anchor"] else None,
        }

    def _set_kill_switch(self, login: int, enabled: bool) -> None:
        self._get_overrides(login)  # ensure row exists
        with self._cx() as cx:
            cx.execute("UPDATE mt5_overrides SET kill_switch=? WHERE login=?", (1 if enabled else 0, login))

    def _update_risk_limits(self, login: int, patch: dict) -> dict:
        ov = self._get_overrides(login)
        merged = {**ov["risk_limits"], **{k: v for k, v in patch.items() if v is not None}}
        with self._cx() as cx:
            cx.execute("UPDATE mt5_overrides SET risk_limits=? WHERE login=?",
                       (json.dumps(merged), login))
        return merged

    def _maybe_set_daily_anchor(self, login: int, balance: float) -> float:
        today = datetime.now(timezone.utc).date().isoformat()
        ov = self._get_overrides(login)
        anchor = ov.get("daily_pnl_anchor")
        if not anchor or anchor.get("date") != today:
            anchor = {"date": today, "balance": float(balance)}
            with self._cx() as cx:
                cx.execute("UPDATE mt5_overrides SET daily_pnl_anchor=? WHERE login=?",
                           (json.dumps(anchor), login))
        return float(anchor["balance"])

    # ---- async public API (matches MT5Cache) ----
    async def put(self, key: str, payload: Any) -> None:
        await asyncio.to_thread(self._put, key, payload)

    async def get(self, key: str) -> dict | None:
        return await asyncio.to_thread(self._get, key)

    async def get_overrides(self, login: int) -> dict:
        return await asyncio.to_thread(self._get_overrides, login)

    async def set_kill_switch(self, login: int, enabled: bool) -> None:
        await asyncio.to_thread(self._set_kill_switch, login, enabled)

    async def update_risk_limits(self, login: int, patch: dict) -> dict:
        return await asyncio.to_thread(self._update_risk_limits, login, patch)

    async def maybe_set_daily_anchor(self, login: int, balance: float) -> float:
        return await asyncio.to_thread(self._maybe_set_daily_anchor, login, balance)

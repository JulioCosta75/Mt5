"""Local SQLite storage for the MT5 bridge.

Stores periodic equity snapshots so we can build an equity curve even before
having a long deal history. Also caches reconstructed equity series so the
backend can fetch fast without re-querying MT5 on every call.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_login INTEGER NOT NULL,
    ts TEXT NOT NULL,          -- ISO 8601 UTC
    equity REAL NOT NULL,
    balance REAL NOT NULL,
    margin REAL NOT NULL,
    free_margin REAL NOT NULL,
    profit REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_equity_snapshots_login_ts
    ON equity_snapshots(account_login, ts);

CREATE TABLE IF NOT EXISTS reconstructed_equity (
    account_login INTEGER NOT NULL,
    ts TEXT NOT NULL,
    equity REAL NOT NULL,
    PRIMARY KEY (account_login, ts)
);
"""


class Storage:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._cx() as cx:
            cx.executescript(SCHEMA)

    @contextmanager
    def _cx(self):
        cx = sqlite3.connect(self.path)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
            cx.commit()
        finally:
            cx.close()

    # ---- snapshots ----
    def insert_snapshot(self, account_login: int, payload: dict):
        with self._cx() as cx:
            cx.execute(
                "INSERT INTO equity_snapshots (account_login, ts, equity, balance, "
                "margin, free_margin, profit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    account_login,
                    datetime.now(timezone.utc).isoformat(),
                    payload.get("equity", 0.0),
                    payload.get("balance", 0.0),
                    payload.get("margin", 0.0),
                    payload.get("margin_free", 0.0),
                    payload.get("profit", 0.0),
                ),
            )

    def list_snapshots(self, account_login: int, limit: int = 5000) -> list[dict]:
        with self._cx() as cx:
            rows = cx.execute(
                "SELECT ts, equity FROM equity_snapshots "
                "WHERE account_login = ? ORDER BY ts ASC LIMIT ?",
                (account_login, limit),
            ).fetchall()
        return [{"t": r["ts"], "equity": r["equity"]} for r in rows]

    # ---- reconstructed ----
    def upsert_reconstructed(self, account_login: int, series: Iterable[dict]):
        with self._cx() as cx:
            cx.executemany(
                "INSERT OR REPLACE INTO reconstructed_equity (account_login, ts, equity) "
                "VALUES (?, ?, ?)",
                [(account_login, p["t"], p["equity"]) for p in series],
            )

    def get_reconstructed(self, account_login: int) -> list[dict]:
        with self._cx() as cx:
            rows = cx.execute(
                "SELECT ts, equity FROM reconstructed_equity "
                "WHERE account_login = ? ORDER BY ts ASC",
                (account_login,),
            ).fetchall()
        return [{"t": r["ts"], "equity": r["equity"]} for r in rows]

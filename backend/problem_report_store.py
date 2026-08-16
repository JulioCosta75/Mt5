"""Persistent SQLite registry for problem reports (collection only — no auto-fix)."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS problem_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    tester TEXT,
    atlas_version TEXT,
    atlas_build TEXT,
    email_status TEXT NOT NULL,
    email_error TEXT,
    email_provider_id TEXT,
    diagnostic_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_problem_reports_created
    ON problem_reports (created_at DESC);
"""


def default_db_path() -> Path:
    env = os.environ.get("ATLAS_SQLITE_PATH")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "data" / "atlas.db"


class ProblemReportStore:
    """Simple append-only history of tester problem reports."""

    def __init__(self, path: str | Path | None = None):
        self.path = str(path or default_db_path())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._cx() as cx:
            cx.executescript(_SCHEMA)

    @contextmanager
    def _cx(self):
        cx = sqlite3.connect(self.path, isolation_level=None)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
        finally:
            cx.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def insert(
        self,
        *,
        tester: str | None,
        atlas_version: str | None,
        atlas_build: str | None,
        diagnostic: dict[str, Any],
        email_status: str = "pending",
    ) -> int:
        with self._cx() as cx:
            cur = cx.execute(
                """
                INSERT INTO problem_reports (
                    created_at, tester, atlas_version, atlas_build,
                    email_status, email_error, email_provider_id, diagnostic_json
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?)
                """,
                (
                    self._now(),
                    (tester or "").strip()[:120] or None,
                    (atlas_version or "")[:64] or None,
                    (atlas_build or "")[:64] or None,
                    email_status,
                    json.dumps(diagnostic, ensure_ascii=False, default=str),
                ),
            )
            return int(cur.lastrowid)

    def update_email(
        self,
        report_id: int,
        *,
        email_status: str,
        email_error: str | None = None,
        email_provider_id: str | None = None,
    ) -> None:
        with self._cx() as cx:
            cx.execute(
                """
                UPDATE problem_reports
                   SET email_status = ?,
                       email_error = ?,
                       email_provider_id = ?
                 WHERE id = ?
                """,
                (
                    email_status,
                    (email_error or None),
                    email_provider_id,
                    int(report_id),
                ),
            )

    def get(self, report_id: int) -> dict | None:
        with self._cx() as cx:
            row = cx.execute(
                "SELECT * FROM problem_reports WHERE id = ?",
                (int(report_id),),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_recent(self, limit: int = 50) -> list[dict]:
        limit = max(1, min(int(limit or 50), 200))
        with self._cx() as cx:
            rows = cx.execute(
                """
                SELECT id, created_at, tester, atlas_version, atlas_build,
                       email_status, email_error, email_provider_id
                  FROM problem_reports
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        raw = d.pop("diagnostic_json", None)
        try:
            d["diagnostic"] = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            d["diagnostic"] = {"raw": raw}
        return d

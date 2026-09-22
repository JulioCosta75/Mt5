"""SQLite persistence for AI usage — ai_usage.db only. Append-only."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from ai_usage.domain.entities import AIUsageRecord


def new_id() -> UUID:
    return uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _row_to_record(row: sqlite3.Row) -> AIUsageRecord:
    return AIUsageRecord(
        id=UUID(row["id"]),
        user_id=row["user_id"],
        mode=row["mode"],
        model=row["model"],
        input_tokens=int(row["input_tokens"]),
        output_tokens=int(row["output_tokens"]),
        estimated_cost_usd=Decimal(row["estimated_cost_usd"]),
        occurred_at=_parse_dt(row["occurred_at"]),
    )


class UsageRepository:
    """SQLite repository isolated from atlas.db, knowledge.db, and notifications.db."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        cx = sqlite3.connect(self.db_path)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA foreign_keys = ON")
        return cx

    @contextmanager
    def _connection(self):
        cx = self._connect()
        try:
            with cx:
                yield cx
        finally:
            cx.close()

    def _init_schema(self) -> None:
        schema_file = Path(__file__).with_name("schema.sql")
        ddl = schema_file.read_text(encoding="utf-8")
        with self._connection() as cx:
            cx.executescript(ddl)

    def insert(self, record: AIUsageRecord) -> AIUsageRecord:
        with self._connection() as cx:
            cx.execute(
                """
                INSERT INTO ai_usage (
                    id, user_id, mode, model, input_tokens, output_tokens,
                    estimated_cost_usd, occurred_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    str(record.id),
                    record.user_id,
                    record.mode,
                    record.model,
                    record.input_tokens,
                    record.output_tokens,
                    str(record.estimated_cost_usd),
                    _iso(record.occurred_at),
                ),
            )
        return record

    def list_for_user(self, user_id: str) -> list[AIUsageRecord]:
        with self._connection() as cx:
            rows = cx.execute(
                """
                SELECT * FROM ai_usage
                WHERE user_id = ?
                ORDER BY occurred_at ASC, rowid ASC
                """,
                (user_id,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def sum_cost_since(
        self,
        *,
        since: datetime,
        user_id: str | None = None,
        until: datetime | None = None,
    ) -> Decimal:
        clauses = ["occurred_at >= ?"]
        params: list = [_iso(since)]
        if until is not None:
            clauses.append("occurred_at < ?")
            params.append(_iso(until))
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        sql = f"SELECT estimated_cost_usd FROM ai_usage WHERE {' AND '.join(clauses)}"
        with self._connection() as cx:
            rows = cx.execute(sql, params).fetchall()
        total = Decimal("0")
        for row in rows:
            total += Decimal(row["estimated_cost_usd"])
        return total

    def count_since(self, *, user_id: str, since: datetime) -> int:
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT COUNT(*) AS n FROM ai_usage
                WHERE user_id = ? AND occurred_at >= ?
                """,
                (user_id, _iso(since)),
            ).fetchone()
        return int(row["n"]) if row else 0

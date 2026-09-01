"""Durable SQLite outbox: crash-safe queue with event_id deduplication."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from telegram_demo_outbound.redact import redact_text

_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    event_id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    provider_message_id TEXT
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class OutboxItem:
    event_id: str
    chat_id: str
    body: str
    status: str
    attempts: int
    provider_message_id: str | None
    last_error: str | None = None


class DurableOutbox:
    """SQLite-backed outbox. Duplicate event_id inserts are no-ops."""

    def __init__(self, path: str, *, secrets: tuple[str, ...] = ()) -> None:
        self.path = path
        self._secrets = secrets
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.isolation_level = None
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def enqueue(self, event_id: str, chat_id: str, body: str) -> str:
        now = _utcnow()
        try:
            self._conn.execute(
                "INSERT INTO outbox ("
                " event_id, chat_id, body, status, attempts,"
                " created_at, updated_at"
                ") VALUES (?, ?, ?, 'pending', 0, ?, ?)",
                (event_id, chat_id, body, now, now),
            )
            return "enqueued"
        except sqlite3.IntegrityError:
            return "duplicate"

    def claim_unsent(self, limit: int = 20) -> list[OutboxItem]:
        now = _utcnow()
        cur = self._conn.cursor()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            rows = cur.execute(
                "SELECT event_id, chat_id, body, status, attempts, provider_message_id, last_error "
                "FROM outbox "
                "WHERE provider_message_id IS NULL "
                "AND status IN ('pending', 'sending') "
                "ORDER BY created_at ASC "
                "LIMIT ?",
                (limit,),
            ).fetchall()
            items = [
                OutboxItem(
                    event_id=row[0],
                    chat_id=row[1],
                    body=row[2],
                    status=row[3],
                    attempts=row[4],
                    provider_message_id=row[5],
                    last_error=row[6],
                )
                for row in rows
            ]
            if items:
                ids = [item.event_id for item in items]
                placeholders = ",".join("?" for _ in ids)
                cur.execute(
                    f"UPDATE outbox SET status='sending', updated_at=? "
                    f"WHERE event_id IN ({placeholders})",
                    [now, *ids],
                )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        return items

    def mark_sent(self, event_id: str, provider_message_id: str) -> None:
        self._conn.execute(
            "UPDATE outbox SET status='sent', provider_message_id=?,"
            " last_error=NULL, updated_at=? WHERE event_id=?",
            (str(provider_message_id), _utcnow(), event_id),
        )

    def mark_retry(self, event_id: str, error: str) -> None:
        safe = redact_text(error, self._secrets)
        self._conn.execute(
            "UPDATE outbox SET status='pending', attempts=attempts+1,"
            " last_error=?, updated_at=? WHERE event_id=? AND status!='sent'",
            (safe, _utcnow(), event_id),
        )

    def get(self, event_id: str) -> OutboxItem | None:
        row = self._conn.execute(
            "SELECT event_id, chat_id, body, status, attempts, provider_message_id, last_error "
            "FROM outbox WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if row is None:
            return None
        return OutboxItem(
            event_id=row[0],
            chat_id=row[1],
            body=row[2],
            status=row[3],
            attempts=row[4],
            provider_message_id=row[5],
            last_error=row[6],
        )

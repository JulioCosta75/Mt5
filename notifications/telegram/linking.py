"""One-time Telegram linking codes and chat_id storage.

Stores only ``chat_id`` against ``(user_id, account_id)`` in notifications.db.
Never stores a phone number.
"""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from notifications.domain.rules import require_account_id, require_user_id

_CODE_BYTES = 9


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class TelegramLinkStore:
    """SQLite link-code and chat_id tables on notifications.db."""

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

    def issue_code(self, user_id: str, account_id: str) -> str:
        user_id = require_user_id(user_id)
        account_id = require_account_id(account_id)
        code = secrets.token_urlsafe(_CODE_BYTES)
        with self._connection() as cx:
            cx.execute(
                """
                INSERT INTO telegram_link_codes (code, user_id, account_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (code, user_id, account_id, _iso(_utcnow())),
            )
        return code

    def consume_code(self, code: str) -> tuple[str, str] | None:
        raw = (code or "").strip()
        if not raw:
            return None
        now = _iso(_utcnow())
        with self._connection() as cx:
            cur = cx.execute(
                """
                UPDATE telegram_link_codes
                   SET consumed_at = ?
                 WHERE code = ? AND consumed_at IS NULL
                """,
                (now, raw),
            )
            if cur.rowcount != 1:
                return None
            row = cx.execute(
                "SELECT user_id, account_id FROM telegram_link_codes WHERE code = ?",
                (raw,),
            ).fetchone()
        if row is None:
            return None
        return str(row["user_id"]), str(row["account_id"])

    def link_chat(self, *, chat_id: str, user_id: str, account_id: str) -> None:
        chat_id = str(chat_id).strip()
        if not chat_id:
            raise ValueError("chat_id is required.")
        user_id = require_user_id(user_id)
        account_id = require_account_id(account_id)
        now = _iso(_utcnow())
        with self._connection() as cx:
            cx.execute(
                "DELETE FROM telegram_chat_links WHERE user_id = ? AND account_id = ?",
                (user_id, account_id),
            )
            cx.execute(
                "DELETE FROM telegram_chat_links WHERE chat_id = ?",
                (chat_id,),
            )
            cx.execute(
                """
                INSERT INTO telegram_chat_links (chat_id, user_id, account_id, linked_at)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, user_id, account_id, now),
            )

    def lookup_chat(self, chat_id: str) -> tuple[str, str] | None:
        raw = str(chat_id).strip()
        if not raw:
            return None
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT user_id, account_id FROM telegram_chat_links
                 WHERE chat_id = ?
                """,
                (raw,),
            ).fetchone()
        if row is None:
            return None
        return str(row["user_id"]), str(row["account_id"])

    def stored_row_blob(self) -> str:
        """Test helper: all stored link values as one string (never for production)."""
        with self._connection() as cx:
            links = cx.execute("SELECT * FROM telegram_chat_links").fetchall()
            codes = cx.execute("SELECT * FROM telegram_link_codes").fetchall()
        parts = []
        for row in list(links) + list(codes):
            parts.extend(str(value) for value in dict(row).values() if value is not None)
        return " ".join(parts)

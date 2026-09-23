"""Linking codes resolve to (user_id, account_id) and store only chat_id."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from notifications.telegram.linking import TelegramLinkStore


def test_issue_and_consume_code_is_one_time():
    with tempfile.TemporaryDirectory() as tmp:
        store = TelegramLinkStore(Path(tmp) / "notifications.db")
        code = store.issue_code("alice", "MT5-5609382")
        assert store.consume_code(code) == ("alice", "MT5-5609382")
        assert store.consume_code(code) is None
        assert store.consume_code("no-such-code") is None
        assert store.consume_code("") is None


def test_link_stores_chat_id_not_phone_and_columns_exclude_phone():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "notifications.db"
        store = TelegramLinkStore(db)
        store.link_chat(chat_id="777", user_id="bob", account_id="MT5-3333")
        assert store.lookup_chat("777") == ("bob", "MT5-3333")
        assert store.lookup_chat("999") is None

        cx = sqlite3.connect(db)
        cx.row_factory = sqlite3.Row
        columns = {
            row["name"]
            for row in cx.execute("PRAGMA table_info(telegram_chat_links)").fetchall()
        }
        cx.close()
        assert "phone" not in columns
        assert "phone_number" not in columns
        assert columns == {"chat_id", "user_id", "account_id", "linked_at"}
        assert "+351" not in store.stored_row_blob()


def test_relink_replaces_previous_chat_for_same_account():
    with tempfile.TemporaryDirectory() as tmp:
        store = TelegramLinkStore(Path(tmp) / "notifications.db")
        store.link_chat(chat_id="1", user_id="alice", account_id="MT5-1111")
        store.link_chat(chat_id="2", user_id="alice", account_id="MT5-1111")
        assert store.lookup_chat("1") is None
        assert store.lookup_chat("2") == ("alice", "MT5-1111")

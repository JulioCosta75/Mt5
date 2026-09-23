"""Command parsing and the fixed informational fallback."""

from __future__ import annotations

import tempfile
from pathlib import Path

from notifications.application.services import PreferenceService
from notifications.infrastructure.repositories import NotificationPreferenceRepository
from notifications.telegram.clients import FakeTelegramClient
from notifications.telegram.commands import (
    HELP_TEXT,
    INFORMATIONAL_REPLY,
    INVALID_CODE_REPLY,
    START_OK_REPLY,
    STOP_OK_REPLY,
    parse_command_text,
    parse_update,
)
from notifications.telegram.handler import TelegramCommandHandler
from notifications.telegram.linking import TelegramLinkStore


def _make_update(text: str, chat_id: int = 4242, update_id: int = 1, extra_message=None):
    message = {
        "message_id": 1,
        "chat": {"id": chat_id, "type": "private"},
        "text": text,
        "from": {"id": chat_id, "first_name": "Ana"},
    }
    if extra_message:
        message.update(extra_message)
    return {"update_id": update_id, "message": message}


def _handler(tmp: str, client: FakeTelegramClient | None = None):
    db = Path(tmp) / "notifications.db"
    prefs = PreferenceService(NotificationPreferenceRepository(db))
    links = TelegramLinkStore(db)
    client = client or FakeTelegramClient()
    return TelegramCommandHandler(client=client, links=links, prefs=prefs), links, prefs, client


def test_parse_start_help_stop_and_fallback():
    assert parse_command_text("/start ABC") == ("start", "ABC")
    assert parse_command_text("/start@AtlasBot ABC") == ("start", "ABC")
    assert parse_command_text("/help") == ("help", None)
    assert parse_command_text("/stop") == ("stop", None)
    assert parse_command_text("/buy EURUSD") == (None, None)
    assert parse_command_text("fecha a posição") == (None, None)
    parsed = parse_update(_make_update("/help"))
    assert parsed is not None
    assert parsed.command == "help"
    assert parsed.chat_id == "4242"


def test_help_sends_fixed_instructions():
    with tempfile.TemporaryDirectory() as tmp:
        handler, _links, _prefs, client = _handler(tmp)
        handler.handle_update(_make_update("/help"))
        assert client.sent == [("4242", HELP_TEXT)]


def test_unknown_text_gets_fixed_informational_reply():
    with tempfile.TemporaryDirectory() as tmp:
        handler, _links, _prefs, client = _handler(tmp)
        handler.handle_update(_make_update("compra agora ouro"))
        handler.handle_update(_make_update("/status", update_id=2))
        handler.handle_update(_make_update("/start", update_id=3))
        assert client.sent[0] == ("4242", INFORMATIONAL_REPLY)
        assert client.sent[1] == ("4242", INFORMATIONAL_REPLY)
        assert client.sent[2] == ("4242", INVALID_CODE_REPLY)


def test_start_resolves_one_time_code_and_stores_only_chat_id():
    phone = "+351912345678"
    with tempfile.TemporaryDirectory() as tmp:
        handler, links, _prefs, client = _handler(tmp)
        code = links.issue_code("alice", "MT5-1111")
        handler.handle_update(
            _make_update(
                f"/start {code}",
                extra_message={
                    "contact": {
                        "phone_number": phone,
                        "first_name": "Ana",
                    }
                },
            )
        )
        assert client.sent == [("4242", START_OK_REPLY)]
        assert links.lookup_chat("4242") == ("alice", "MT5-1111")
        blob = links.stored_row_blob()
        assert phone not in blob
        assert "351912345678" not in blob
        assert "phone" not in blob.lower()
        assert links.consume_code(code) is None


def test_stop_deactivates_telegram_preferences_for_that_chat():
    with tempfile.TemporaryDirectory() as tmp:
        handler, links, prefs, client = _handler(tmp)
        prefs.create(
            actor="alice",
            user_id="alice",
            account_id="MT5-1111",
            alert_type="risk_drawdown",
            priority="high",
            frequency="immediate",
            channel="telegram",
            active=True,
        )
        prefs.create(
            actor="alice",
            user_id="alice",
            account_id="MT5-1111",
            alert_type="periodic_report",
            priority="low",
            frequency="digest",
            channel="email",
            active=True,
        )
        code = links.issue_code("alice", "MT5-1111")
        handler.handle_update(_make_update(f"/start {code}"))
        handler.handle_update(_make_update("/stop", update_id=2))
        assert client.sent[-1] == ("4242", STOP_OK_REPLY)
        rows = {row.channel: row.active for row in prefs.list_for_account("alice", "MT5-1111")}
        assert rows["telegram"] is False
        assert rows["email"] is True


def test_poll_once_uses_fake_client_and_offset():
    with tempfile.TemporaryDirectory() as tmp:
        client = FakeTelegramClient()
        handler, links, _prefs, client = _handler(tmp, client=client)
        code = links.issue_code("bob", "MT5-2222")
        client.queue_update(_make_update(f"/start {code}", chat_id=99, update_id=10))
        client.queue_update(_make_update("vende tudo", chat_id=99, update_id=11))
        next_offset = handler.poll_once(offset=10)
        assert next_offset == 12
        assert client.sent[0] == ("99", START_OK_REPLY)
        assert client.sent[1] == ("99", INFORMATIONAL_REPLY)

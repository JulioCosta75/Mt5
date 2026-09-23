"""Dispatch parsed Telegram commands. One-way informational channel only."""

from __future__ import annotations

from notifications.application.services import PreferenceService
from notifications.telegram.clients import TelegramClient
from notifications.telegram.commands import (
    HELP_TEXT,
    INFORMATIONAL_REPLY,
    INVALID_CODE_REPLY,
    START_OK_REPLY,
    STOP_OK_REPLY,
    STOP_UNKNOWN_REPLY,
    parse_update,
)
from notifications.telegram.linking import TelegramLinkStore


class TelegramCommandHandler:
    """Handle /start, /help, /stop. Anything else gets the fixed reply."""

    def __init__(
        self,
        *,
        client: TelegramClient,
        links: TelegramLinkStore,
        prefs: PreferenceService,
    ):
        self.client = client
        self.links = links
        self.prefs = prefs

    def handle_update(self, update: dict) -> int | None:
        parsed = parse_update(update)
        update_id = update.get("update_id")
        if parsed is None:
            return int(update_id) if update_id is not None else None
        if parsed.command == "help":
            reply = HELP_TEXT
        elif parsed.command == "start":
            reply = self._handle_start(parsed.chat_id, parsed.argument)
        elif parsed.command == "stop":
            reply = self._handle_stop(parsed.chat_id)
        else:
            reply = INFORMATIONAL_REPLY
        self.client.send_message(parsed.chat_id, reply)
        return int(update_id) if update_id is not None else None

    def poll_once(self, offset: int | None = None) -> int | None:
        """Ask Telegram for new messages (long-poll on the real adapter)."""
        updates = self.client.get_updates(offset)
        next_offset = offset
        for update in updates:
            seen = self.handle_update(update)
            if seen is None:
                continue
            candidate = seen + 1
            if next_offset is None or candidate > next_offset:
                next_offset = candidate
        return next_offset

    def _handle_start(self, chat_id: str, code: str | None) -> str:
        scope = self.links.consume_code(code or "")
        if scope is None:
            return INVALID_CODE_REPLY
        user_id, account_id = scope
        self.links.link_chat(chat_id=chat_id, user_id=user_id, account_id=account_id)
        return START_OK_REPLY

    def _handle_stop(self, chat_id: str) -> str:
        scope = self.links.lookup_chat(chat_id)
        if scope is None:
            return STOP_UNKNOWN_REPLY
        user_id, account_id = scope
        for pref in self.prefs.list_for_account(user_id, account_id):
            if pref.channel != "telegram" or not pref.active:
                continue
            self.prefs.update(
                actor=user_id,
                user_id=user_id,
                account_id=account_id,
                preference_id=pref.id,
                active=False,
            )
        return STOP_OK_REPLY

"""Notifications Stage 2a — isolated Telegram adapter (no webhook).

This package is **not** imported by Phase 2. No ``server.py`` routes, no
frontend, no alert-engine wiring. Automated tests use ``FakeTelegramClient``
only — no bot token and no network.

Atlas runs on a local machine without a public URL, so the adapter uses
Bot API long-polling (``getUpdates``) rather than webhooks.
"""

from notifications.telegram.clients import (
    FakeTelegramClient,
    MissingBotTokenError,
    TelegramAdapter,
    TelegramClientError,
)
from notifications.telegram.commands import INFORMATIONAL_REPLY
from notifications.telegram.handler import TelegramCommandHandler
from notifications.telegram.linking import TelegramLinkStore

__all__ = [
    "FakeTelegramClient",
    "INFORMATIONAL_REPLY",
    "MissingBotTokenError",
    "TelegramAdapter",
    "TelegramClientError",
    "TelegramCommandHandler",
    "TelegramLinkStore",
]

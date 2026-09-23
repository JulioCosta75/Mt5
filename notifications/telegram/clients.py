"""Telegram HTTP adapter. Tests use FakeTelegramClient (zero network).

``TelegramAdapter`` lazy-imports ``httpx`` or ``requests`` inside the
HTTP methods so importing this module never requires those packages or
``TELEGRAM_BOT_TOKEN``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

TELEGRAM_API_ROOT = "https://api.telegram.org"
DEFAULT_LONG_POLL_TIMEOUT = 25


class MissingBotTokenError(RuntimeError):
    """Raised when TELEGRAM_BOT_TOKEN is unset. Message never includes a token."""


class TelegramClientError(RuntimeError):
    """Raised when the real adapter cannot complete a call. Never includes a token."""


class TelegramClient(Protocol):
    def send_message(self, chat_id: str | int, text: str) -> None:
        """Send one informational text message."""

    def get_updates(self, offset: int | None = None) -> list[dict]:
        """Long-poll for new updates (Atlas has no public webhook URL)."""


def _env_bot_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def _scrub(message: str, secret: str) -> str:
    if secret and secret in message:
        return message.replace(secret, "[redacted]")
    return message


@dataclass
class FakeTelegramClient:
    """Deterministic in-memory client. No network. No token."""

    sent: list[tuple[str, str]] = field(default_factory=list)
    queued: list[dict] = field(default_factory=list)

    def send_message(self, chat_id: str | int, text: str) -> None:
        self.sent.append((str(chat_id), text))

    def get_updates(self, offset: int | None = None) -> list[dict]:
        items: list[dict] = []
        for update in self.queued:
            update_id = int(update.get("update_id", 0))
            if offset is None or update_id >= offset:
                items.append(update)
        return items

    def queue_update(self, update: dict) -> None:
        self.queued.append(update)


class TelegramAdapter:
    """Real Bot API caller. HTTP import is inside send_message / get_updates."""

    def __init__(self, *, long_poll_timeout: int = DEFAULT_LONG_POLL_TIMEOUT):
        self.long_poll_timeout = int(long_poll_timeout)

    def send_message(self, chat_id: str | int, text: str) -> None:
        token = _require_token()
        payload = {"chat_id": str(chat_id), "text": text}
        self._post(token, "sendMessage", payload)

    def get_updates(self, offset: int | None = None) -> list[dict]:
        token = _require_token()
        payload: dict[str, str | int] = {"timeout": self.long_poll_timeout}
        if offset is not None:
            payload["offset"] = int(offset)
        data = self._get(token, "getUpdates", payload)
        result = data.get("result") if isinstance(data, dict) else None
        if not isinstance(result, list):
            return []
        return result

    def _post(self, token: str, method: str, payload: dict) -> dict:
        try:
            import httpx
        except ImportError:
            try:
                import requests
            except ImportError as exc:
                raise TelegramClientError(
                    "neither httpx nor requests is installed; tests use "
                    "FakeTelegramClient and do not require a Telegram HTTP client."
                ) from exc
            return self._requests_call(requests, "POST", token, method, payload)
        return self._httpx_call(httpx, "POST", token, method, payload)

    def _get(self, token: str, method: str, payload: dict) -> dict:
        try:
            import httpx
        except ImportError:
            try:
                import requests
            except ImportError as exc:
                raise TelegramClientError(
                    "neither httpx nor requests is installed; tests use "
                    "FakeTelegramClient and do not require a Telegram HTTP client."
                ) from exc
            return self._requests_call(requests, "GET", token, method, payload)
        return self._httpx_call(httpx, "GET", token, method, payload)

    def _httpx_call(self, httpx, verb: str, token: str, method: str, payload: dict) -> dict:
        url = _method_url(token, method)
        timeout = self.long_poll_timeout + 5
        try:
            if verb == "GET":
                response = httpx.get(url, params=payload, timeout=timeout)
            else:
                response = httpx.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise TelegramClientError(_scrub(str(exc), token)) from None
        return _ok_payload(data, token)

    def _requests_call(self, requests, verb: str, token: str, method: str, payload: dict) -> dict:
        url = _method_url(token, method)
        timeout = self.long_poll_timeout + 5
        try:
            if verb == "GET":
                response = requests.get(url, params=payload, timeout=timeout)
            else:
                response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise TelegramClientError(_scrub(str(exc), token)) from None
        return _ok_payload(data, token)


def _require_token() -> str:
    token = _env_bot_token()
    if not token:
        raise MissingBotTokenError(
            "TELEGRAM_BOT_TOKEN is not set. Notifications Stage 2a will not "
            "contact Telegram without a token."
        )
    return token


def _method_url(token: str, method: str) -> str:
    return f"{TELEGRAM_API_ROOT}/bot{token}/{method}"


def _ok_payload(data: object, token: str) -> dict:
    if not isinstance(data, dict):
        raise TelegramClientError("Telegram API returned a non-object payload.")
    if not data.get("ok", False):
        description = _scrub(str(data.get("description") or "request failed"), token)
        raise TelegramClientError(description)
    return data

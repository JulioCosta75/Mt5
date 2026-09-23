"""TELEGRAM_BOT_TOKEN is env-only and scrubbed from errors."""

from __future__ import annotations

import sys
import types

import pytest

from notifications.telegram.clients import (
    MissingBotTokenError,
    TelegramAdapter,
    TelegramClientError,
    _env_bot_token,
)


def test_token_comes_from_environment_only(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert _env_bot_token() == ""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token-value")
    assert _env_bot_token() == "secret-token-value"


def test_missing_token_error_does_not_include_a_secret(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(MissingBotTokenError, match="TELEGRAM_BOT_TOKEN is not set") as raised:
        TelegramAdapter().send_message("1", "hello")
    assert "secret" not in str(raised.value).lower()


def test_http_error_scrubs_token_from_message(monkeypatch):
    token = "123456:ABC-SECRET-TOKEN"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)

    fake = types.ModuleType("httpx")

    class _BoomResponse:
        def raise_for_status(self):
            raise RuntimeError(f"POST https://api.telegram.org/bot{token}/sendMessage failed")

    def _post(url, json=None, timeout=None):
        return _BoomResponse()

    def _get(url, params=None, timeout=None):
        raise AssertionError("get_updates should not run in this test")

    fake.post = _post
    fake.get = _get
    monkeypatch.setitem(sys.modules, "httpx", fake)
    with pytest.raises(TelegramClientError) as raised:
        TelegramAdapter().send_message("1", "hello")
    message = str(raised.value)
    assert token not in message
    assert "[redacted]" in message

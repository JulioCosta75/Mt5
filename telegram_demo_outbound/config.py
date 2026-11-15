"""Environment configuration. Fail closed unless APP_MODE is exactly 'demo'."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from telegram_demo_outbound.constants import (
    APP_MODE_ENV,
    CHAT_ID_ENV,
    DEFAULT_OUTBOX_PATH,
    DEFAULT_TRANSPORT,
    DEMO_APP_MODE,
    HTTP_TRANSPORT,
    OUTBOX_PATH_ENV,
    TOKEN_ENV,
    TRANSPORT_ENV,
)
from telegram_demo_outbound.errors import (
    FailClosedError,
    MissingAllowlistError,
    MissingTokenError,
)


def read_app_mode(env: Mapping[str, str] | None = None) -> str | None:
    source = os.environ if env is None else env
    if APP_MODE_ENV not in source:
        return None
    return source[APP_MODE_ENV]


def is_demo_app_mode(env: Mapping[str, str] | None = None) -> bool:
    """True only when APP_MODE is exactly 'demo'. Never inferred."""
    return read_app_mode(env) == DEMO_APP_MODE


def require_demo_app_mode(env: Mapping[str, str] | None = None) -> str:
    mode = read_app_mode(env)
    if mode != DEMO_APP_MODE:
        raise FailClosedError(
            "APP_MODE is not exactly 'demo'; refusing to send via real transport"
        )
    return DEMO_APP_MODE


def read_transport_name(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    raw = source.get(TRANSPORT_ENV)
    if raw is None or raw == "":
        return DEFAULT_TRANSPORT
    return raw


def require_bot_token(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    token = source.get(TOKEN_ENV)
    if token is None or token == "":
        raise MissingTokenError(
            "TELEGRAM_BOT_TOKEN is absent; refusing to operate"
        )
    return token


def require_allowlist(env: Mapping[str, str] | None = None) -> frozenset[str]:
    source = os.environ if env is None else env
    chat_id = source.get(CHAT_ID_ENV)
    if chat_id is None or str(chat_id).strip() == "":
        raise MissingAllowlistError(
            "TELEGRAM_CHAT_ID is absent; refusing to send"
        )
    normalized = str(chat_id).strip()
    return frozenset({normalized})


def read_outbox_path(env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return source.get(OUTBOX_PATH_ENV) or DEFAULT_OUTBOX_PATH


@dataclass(frozen=True)
class RuntimeConfig:
    app_mode: str | None
    transport_name: str
    outbox_path: str

    @property
    def real_http_allowed(self) -> bool:
        return self.app_mode == DEMO_APP_MODE and self.transport_name == HTTP_TRANSPORT


def load_runtime_config(env: Mapping[str, str] | None = None) -> RuntimeConfig:
    return RuntimeConfig(
        app_mode=read_app_mode(env),
        transport_name=read_transport_name(env),
        outbox_path=read_outbox_path(env),
    )

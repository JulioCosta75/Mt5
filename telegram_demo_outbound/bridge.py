"""Outbound bridge: prefix, allowlist, durable queue, rate limit, transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from telegram_demo_outbound.config import (
    load_runtime_config,
    require_allowlist,
    require_bot_token,
    require_demo_app_mode,
)
from telegram_demo_outbound.constants import DEFAULT_TRANSPORT, HTTP_TRANSPORT, MAX_FLUSH_ATTEMPTS
from telegram_demo_outbound.errors import (
    ChatNotAllowlistedError,
    FailClosedError,
    PermanentTransportError,
    RetryableTransportError,
)
from telegram_demo_outbound.events import ensure_prefix
from telegram_demo_outbound.queue import DurableOutbox
from telegram_demo_outbound.rate_limit import RateLimiter
from telegram_demo_outbound.transport import (
    HttpClient,
    MockTransport,
    SendResult,
    TelegramHttpTransport,
)


@dataclass
class FlushResult:
    sent: int = 0
    skipped_duplicate: int = 0
    retried: int = 0
    failed: int = 0


class OutboundBridge:
    def __init__(
        self,
        *,
        transport: MockTransport | TelegramHttpTransport,
        outbox: DurableOutbox,
        allowlist: frozenset[str],
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.transport = transport
        self.outbox = outbox
        self.allowlist = allowlist
        self.rate_limiter = rate_limiter or RateLimiter()

    def enqueue(self, event_id: str, chat_id: str, text: str) -> str:
        if str(chat_id) not in self.allowlist:
            raise ChatNotAllowlistedError(
                "chat_id is not on the allowlist; refusing to send"
            )
        prefixed = ensure_prefix(text)
        return self.outbox.enqueue(event_id, str(chat_id), prefixed)

    def flush(self, *, limit: int = 20) -> FlushResult:
        result = FlushResult()
        for item in self.outbox.claim_unsent(limit=limit):
            existing = self.outbox.get(item.event_id)
            if existing is not None and existing.provider_message_id:
                result.skipped_duplicate += 1
                continue
            if item.attempts >= MAX_FLUSH_ATTEMPTS:
                result.failed += 1
                continue
            self.rate_limiter.wait(item.chat_id)
            try:
                sent: SendResult = self.transport.send_message(item.chat_id, item.body)
            except RetryableTransportError as exc:
                self.outbox.mark_retry(item.event_id, str(exc))
                result.retried += 1
                continue
            except (FailClosedError, ChatNotAllowlistedError, PermanentTransportError):
                raise
            if sent.ok and sent.provider_message_id:
                self.outbox.mark_sent(item.event_id, sent.provider_message_id)
                result.sent += 1
            else:
                self.outbox.mark_retry(item.event_id, "send returned without id")
                result.retried += 1
        return result


def build_bridge_from_env(
    env: Mapping[str, str] | None = None,
    *,
    http: HttpClient | None = None,
    outbox_path: str | None = None,
    allowlist: frozenset[str] | None = None,
    transport: MockTransport | TelegramHttpTransport | None = None,
) -> OutboundBridge:
    """Factory: mock transport by default. Real HTTP only when explicitly selected
    AND APP_MODE is exactly 'demo'. Any other APP_MODE fail-closes.
    """
    cfg = load_runtime_config(env)
    path = outbox_path or cfg.outbox_path

    if transport is not None:
        resolved_allowlist = allowlist if allowlist is not None else require_allowlist(env)
        outbox = DurableOutbox(path, secrets=tuple(resolved_allowlist))
        return OutboundBridge(
            transport=transport,
            outbox=outbox,
            allowlist=resolved_allowlist,
        )

    if cfg.transport_name == DEFAULT_TRANSPORT or cfg.transport_name == "mock":
        resolved_allowlist = allowlist if allowlist is not None else require_allowlist(env)
        outbox = DurableOutbox(path, secrets=tuple(resolved_allowlist))
        return OutboundBridge(
            transport=MockTransport(),
            outbox=outbox,
            allowlist=resolved_allowlist,
        )

    if cfg.transport_name == HTTP_TRANSPORT:
        require_demo_app_mode(env)
        token = require_bot_token(env)
        resolved_allowlist = allowlist if allowlist is not None else require_allowlist(env)
        outbox = DurableOutbox(path, secrets=(token, *resolved_allowlist))
        http_transport = TelegramHttpTransport(
            token=token,
            allowlist=resolved_allowlist,
            app_mode=cfg.app_mode,
            http=http,
        )
        return OutboundBridge(
            transport=http_transport,
            outbox=outbox,
            allowlist=resolved_allowlist,
        )

    raise FailClosedError(
        "unknown TELEGRAM_TRANSPORT; refusing to send (fail closed)"
    )

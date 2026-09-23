"""Typed failures for the Telegram DEMO outbound bridge."""


class TelegramDemoError(Exception):
    """Base error. Messages must never contain secret values."""


class FailClosedError(TelegramDemoError):
    """Real transport refused to send (APP_MODE is not exactly 'demo')."""


class MissingTokenError(TelegramDemoError):
    """TELEGRAM_BOT_TOKEN is absent; the real transport will not operate."""


class MissingAllowlistError(TelegramDemoError):
    """No validated chat_id allowlist is available."""


class ChatNotAllowlistedError(TelegramDemoError):
    """Target chat_id is not Julio's validated allowlisted chat."""


class RetryableTransportError(TelegramDemoError):
    """Transient send failure; the outbox should retry the same event_id."""


class PermanentTransportError(TelegramDemoError):
    """Non-retryable send failure (still must not include secrets)."""

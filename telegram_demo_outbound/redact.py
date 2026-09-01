"""Secret redaction. Token and chat_id values must never appear in output."""

from __future__ import annotations

import re
from typing import Any, Iterable

# Bot tokens look like <digits>:<secret>. Never log or return the raw value.
_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")
_REDACTED = "[REDACTED]"
_REDACTED_CHAT = "[REDACTED_CHAT_ID]"


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    """Replace known secrets and token-shaped substrings."""
    out = text
    for secret in secrets:
        if secret and secret in out:
            out = out.replace(secret, _REDACTED)
    out = _TOKEN_RE.sub(_REDACTED, out)
    return out


def sanitize_telegram_json(
    payload: Any,
    *,
    secrets: Iterable[str] = (),
    in_chat: bool = False,
    in_from: bool = False,
) -> Any:
    """Return a copy of a Telegram API payload with secrets removed.

    Bot identity (is_bot=true) ids are kept. User/chat ids are replaced.
    Token-shaped strings are always replaced.
    """
    secret_set = {str(s) for s in secrets if s}

    def _walk(obj: Any, *, in_chat: bool, in_from: bool, is_bot: Any) -> Any:
        if isinstance(obj, dict):
            local_is_bot = obj.get("is_bot", is_bot)
            out: dict[str, Any] = {}
            for key, value in obj.items():
                child_chat = in_chat or key == "chat"
                child_from = in_from or key == "from"
                key_l = str(key).lower()
                redact_id = (
                    key_l in {"chat_id", "user_id"}
                    or (key_l == "id" and in_chat)
                    or (key_l == "id" and in_from and local_is_bot is False)
                )
                if redact_id:
                    out[key] = _REDACTED_CHAT
                else:
                    out[key] = _walk(
                        value,
                        in_chat=child_chat,
                        in_from=child_from,
                        is_bot=local_is_bot,
                    )
            return out
        if isinstance(obj, list):
            return [
                _walk(item, in_chat=in_chat, in_from=in_from, is_bot=is_bot)
                for item in obj
            ]
        if isinstance(obj, str):
            if obj in secret_set:
                return _REDACTED_CHAT
            return redact_text(obj, secret_set)
        if isinstance(obj, int) and in_chat:
            return _REDACTED_CHAT
        if isinstance(obj, int) and str(obj) in secret_set:
            return _REDACTED_CHAT
        return obj

    return _walk(payload, in_chat=in_chat, in_from=in_from, is_bot=None)


def exception_text(exc: BaseException, secrets: Iterable[str] = ()) -> str:
    """Stringify an exception without leaking secrets (including URLs)."""
    return redact_text(f"{type(exc).__name__}: {exc}", secrets)

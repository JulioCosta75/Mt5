"""LLM client protocol for Educador Stage 2.

``FakeLLMClient`` is the test path (zero network). ``AnthropicLLMClient``
lazy-imports the SDK inside ``generate`` so importing this module never
requires ``anthropic`` or an API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol


class MissingAPIKeyError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is unset. Message never includes a key."""


class LLMClientError(RuntimeError):
    """Raised when the real client cannot complete a call. Never includes a key."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(Protocol):
    def generate(self, prompt: str) -> LLMResponse:
        """Return model text and the provider's own token counts."""


@dataclass
class FakeLLMClient:
    """Deterministic canned response. No network. No SDK."""

    text: str = (
        "O spread é a diferença entre o preço de compra e o de venda. "
        "Isto é uma explicação geral, não um conselho financeiro."
    )
    input_tokens: int = 12
    output_tokens: int = 24
    calls: list[str] = field(default_factory=list)

    def generate(self, prompt: str) -> LLMResponse:
        self.calls.append(prompt)
        return LLMResponse(
            text=self.text,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


_MODEL_IDS = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
}


def _env_api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def _scrub(message: str, secret: str) -> str:
    if secret and secret in message:
        return message.replace(secret, "[redacted]")
    return message


class AnthropicLLMClient:
    """Real Anthropic caller. SDK import is inside ``generate`` only."""

    def __init__(self, *, model: str = "haiku"):
        from ai_usage.application.services import route_model

        self.model = route_model(model)

    def generate(self, prompt: str) -> LLMResponse:
        key = _env_api_key()
        if not key:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Educador Stage 2 will not fabricate an answer."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise LLMClientError(
                "the anthropic package is not installed; this stage does not "
                "require it for tests or for CLI use without a key."
            ) from exc
        model_id = _MODEL_IDS.get(self.model, _MODEL_IDS["haiku"])
        try:
            client = anthropic.Anthropic(api_key=key)
            message = client.messages.create(
                model=model_id,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except MissingAPIKeyError:
            raise
        except Exception as exc:
            raise LLMClientError(_scrub(str(exc), key)) from None
        text_parts = []
        for block in getattr(message, "content", ()) or ():
            piece = getattr(block, "text", None)
            if piece:
                text_parts.append(piece)
        usage = getattr(message, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return LLMResponse(
            text="".join(text_parts),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

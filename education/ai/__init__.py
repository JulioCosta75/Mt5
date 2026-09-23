"""Educador Stage 2 — budget-guarded LLM adapter (no key required to import)."""

from education.ai.clients import AnthropicLLMClient, FakeLLMClient, LLMResponse, MissingAPIKeyError
from education.ai.service import Answer, answer_educador_question, build_educador_prompt

__all__ = [
    "Answer",
    "AnthropicLLMClient",
    "FakeLLMClient",
    "LLMResponse",
    "MissingAPIKeyError",
    "answer_educador_question",
    "build_educador_prompt",
]

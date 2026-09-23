"""Output filter for Educador replies (Contexto de Mercado — no financial advice)."""

from __future__ import annotations

from dataclasses import dataclass

# Phrases decided for the Educador/Comunicador safety filter. Matching is
# case-insensitive substring search on the model text.
BLOCKED_PHRASES: tuple[str, ...] = (
    "deverias",
    "recomendo",
    "compra agora",
)

SAFE_FALLBACK = (
    "Não posso formular isto como um conselho de compra ou venda. "
    "Posso explicar o conceito em termos gerais. "
    "Isto é educação, não uma recomendação personalizada."
)


@dataclass(frozen=True)
class FilterResult:
    allowed: bool
    text: str
    hits: tuple[str, ...]


def filter_educador_output(text: str) -> FilterResult:
    """Return the original text, or a safe fallback if a blocked phrase appears.

    The original text is never returned as-is when a phrase hits.
    """
    lowered = (text or "").casefold()
    hits = tuple(phrase for phrase in BLOCKED_PHRASES if phrase.casefold() in lowered)
    if hits:
        return FilterResult(allowed=False, text=SAFE_FALLBACK, hits=hits)
    return FilterResult(allowed=True, text=text, hits=())

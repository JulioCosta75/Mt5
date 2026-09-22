"""Lookup for the closed Stage 1 Educador glossary.

Unknown ids return ``None``. This module never generates, infers, or
fills in content for a concept that is not in the bundled catalog.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from education.domain.entities import Explanation

_CONTENT_PATH = Path(__file__).resolve().parent / "content" / "glossary.json"

# Closed set for Stage 1. Order matches the founder request.
REQUIRED_CONCEPT_IDS: tuple[str, ...] = (
    "metatrader5",
    "candles",
    "spread",
    "orders",
    "market_sessions",
    "trends",
    "drawdown",
    "expert_advisors",
    "backtest_demo_live",
)


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, dict]:
    raw = json.loads(_CONTENT_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("education/content/glossary.json must be a JSON object")
    return raw


def list_concept_ids() -> tuple[str, ...]:
    """Stable ids present in the bundled catalog."""
    return tuple(_load_catalog().keys())


def get_explanation(concept_id: str) -> Explanation | None:
    """Return the bundled explanation for ``concept_id``, or ``None``.

    Exact id match only (leading/trailing whitespace ignored). Does not
    guess nearby names, aliases, or missing entries.
    """
    if not isinstance(concept_id, str):
        return None
    data = _load_catalog().get(concept_id.strip())
    if data is None:
        return None
    return Explanation(
        id=str(data["id"]),
        title=str(data["title"]),
        definition=str(data["definition"]),
        example=str(data["example"]),
    )

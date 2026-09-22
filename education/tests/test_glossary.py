"""Closed-set glossary: nine concepts, no fabrication, non-empty fields."""

from __future__ import annotations

from education.catalog import REQUIRED_CONCEPT_IDS, get_explanation, list_concept_ids
from education.domain.entities import Explanation

# Founder Stage 1 closed set — kept here so the test does not merely
# echo the production constant against itself.
FOUNDER_CONCEPT_IDS = (
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


def test_required_concept_count_is_nine():
    assert len(FOUNDER_CONCEPT_IDS) == 9
    assert len(REQUIRED_CONCEPT_IDS) == 9
    assert tuple(REQUIRED_CONCEPT_IDS) == FOUNDER_CONCEPT_IDS


def test_all_nine_required_concepts_present_and_retrievable_by_id():
    catalog_ids = list_concept_ids()
    assert set(catalog_ids) == set(FOUNDER_CONCEPT_IDS)
    for concept_id in FOUNDER_CONCEPT_IDS:
        item = get_explanation(concept_id)
        assert isinstance(item, Explanation), concept_id
        assert item.id == concept_id


def test_unknown_concept_id_returns_none_without_exception():
    for unknown in ("", "  ", "pip", "spreadd", "rsi", "unknown", "metatrader"):
        assert get_explanation(unknown) is None


def test_non_string_concept_id_returns_none():
    assert get_explanation(None) is None  # type: ignore[arg-type]
    assert get_explanation(123) is None  # type: ignore[arg-type]


def test_unknown_id_does_not_fabricate_nearby_content():
    nearby = get_explanation("spreadd")
    spread = get_explanation("spread")
    assert nearby is None
    assert spread is not None
    assert spread.id == "spread"


def test_each_entry_has_nonempty_definition_and_example():
    for concept_id in FOUNDER_CONCEPT_IDS:
        item = get_explanation(concept_id)
        assert item is not None
        assert item.title.strip(), concept_id
        assert item.definition.strip(), concept_id
        assert item.example.strip(), concept_id
        assert item.definition.strip() != item.example.strip(), concept_id


def test_whitespace_around_known_id_still_resolves():
    item = get_explanation("  spread  ")
    assert item is not None
    assert item.id == "spread"


def test_content_is_generic_with_no_account_identifiers():
    for concept_id in FOUNDER_CONCEPT_IDS:
        item = get_explanation(concept_id)
        assert item is not None
        blob = f"{item.title}\n{item.definition}\n{item.example}"
        assert "MT5-" not in blob
        assert "account_id" not in blob

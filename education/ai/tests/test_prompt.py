"""Prompt construction never includes account or user financial fields."""

from __future__ import annotations

import inspect

from education.ai.service import answer_educador_question, build_educador_prompt
from education.catalog import get_explanation


FORBIDDEN_PARAM_NAMES = {
    "account_id",
    "account_login",
    "balance",
    "equity",
    "profit",
    "positions",
    "mt5_login",
    "financial",
}


def test_answer_function_has_no_account_or_financial_parameters():
    names = set(inspect.signature(answer_educador_question).parameters)
    assert names.isdisjoint(FORBIDDEN_PARAM_NAMES)
    assert "question" in names
    assert "concept_id" in names
    assert "user_id" in names  # budget only; must not appear in the prompt


def test_built_prompt_does_not_include_user_id_or_account_fields():
    user_marker = "alice_unique_user_xyz"
    prompt = build_educador_prompt(concept_id="spread", question="O que é o spread?")
    assert user_marker not in prompt
    assert "account_id" not in prompt
    assert "MT5-" not in prompt
    assert "equity" not in prompt.casefold()
    assert "balance" not in prompt.casefold()
    spread = get_explanation("spread")
    assert spread is not None
    assert spread.definition in prompt
    assert spread.example in prompt
    assert "O que é o spread?" in prompt


def test_unknown_concept_does_not_invent_catalog_text():
    prompt = build_educador_prompt(concept_id="pip", question="O que é um pip?")
    assert "Não existe entrada de glossário" in prompt
    candles = get_explanation("candles")
    assert candles is not None
    assert candles.definition not in prompt

"""Blocked financial-advice phrases are never returned as-is."""

from __future__ import annotations

from pathlib import Path

from ai_usage.application.services import UsageService
from ai_usage.infrastructure.repositories import UsageRepository
from education.ai.clients import FakeLLMClient
from education.ai.filter import SAFE_FALLBACK, filter_educador_output
from education.ai.service import answer_educador_question


def test_filter_catches_deverias_comprar():
    result = filter_educador_output("Deverias comprar EURUSD nesta sessão.")
    assert result.allowed is False
    assert result.text == SAFE_FALLBACK
    assert "deverias" in result.hits
    assert result.text != "Deverias comprar EURUSD nesta sessão."


def test_fake_response_with_deverias_comprar_is_not_returned(tmp_path: Path):
    usage = UsageService(UsageRepository(tmp_path / "ai_usage.db"))
    original = "Na minha opinião deverias comprar agora porque recomendo este par."
    client = FakeLLMClient(text=original, input_tokens=9, output_tokens=13)
    answer = answer_educador_question(
        user_id="alice",
        tier="free",
        question="Devo entrar em EURUSD?",
        client=client,
        usage=usage,
        concept_id="spread",
    )
    assert client.calls  # the call happened; usage is still recorded
    assert answer.blocked is True
    assert answer.text == SAFE_FALLBACK
    assert answer.text != original
    assert "deverias" not in answer.text.casefold()
    assert "compra agora" not in answer.text.casefold()
    rows = usage.list_for_user("alice")
    assert rows[0].input_tokens == 9
    assert rows[0].output_tokens == 13


def test_clean_fake_response_is_returned_as_is(tmp_path: Path):
    usage = UsageService(UsageRepository(tmp_path / "ai_usage.db"))
    text = "O spread é a diferença entre o preço de compra e o de venda."
    client = FakeLLMClient(text=text)
    answer = answer_educador_question(
        user_id="alice",
        tier="free",
        question="O que é o spread?",
        client=client,
        usage=usage,
        concept_id="spread",
    )
    assert answer.blocked is False
    assert answer.text == text

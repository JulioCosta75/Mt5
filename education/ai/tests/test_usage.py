"""A successful fake call records the fake's own token counts."""

from __future__ import annotations

from pathlib import Path

from ai_usage.application.services import UsageService
from ai_usage.infrastructure.repositories import UsageRepository
from education.ai.clients import FakeLLMClient
from education.ai.service import answer_educador_question


def test_successful_fake_call_records_client_token_counts(tmp_path: Path):
    usage = UsageService(UsageRepository(tmp_path / "ai_usage.db"))
    client = FakeLLMClient(
        text="O spread é a diferença entre compra e venda. Explicação geral.",
        input_tokens=111,
        output_tokens=222,
    )
    answer = answer_educador_question(
        user_id="alice",
        tier="free",
        question="O que é o spread?",
        client=client,
        usage=usage,
        concept_id="spread",
    )
    assert len(client.calls) == 1
    assert answer.limit_reached is False
    assert answer.blocked is False
    assert answer.input_tokens == 111
    assert answer.output_tokens == 222
    assert answer.usage_id is not None
    rows = usage.list_for_user("alice")
    assert len(rows) == 1
    assert rows[0].input_tokens == 111
    assert rows[0].output_tokens == 222
    assert rows[0].mode == "educador"
    assert rows[0].model == "haiku"
    assert rows[0].user_id == "alice"


def test_bob_does_not_see_alice_usage(tmp_path: Path):
    usage = UsageService(UsageRepository(tmp_path / "ai_usage.db"))
    client = FakeLLMClient()
    answer_educador_question(
        user_id="alice",
        tier="free",
        question="O que é uma vela?",
        client=client,
        usage=usage,
        concept_id="candles",
    )
    assert usage.list_for_user("bob") == []

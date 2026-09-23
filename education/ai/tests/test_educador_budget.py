"""Budget guard denial skips the LLM call entirely."""

from __future__ import annotations

from pathlib import Path

from ai_usage.application.services import UsageService
from ai_usage.infrastructure.repositories import UsageRepository
from education.ai.clients import FakeLLMClient
from education.ai.service import LIMIT_REACHED_TEXT, answer_educador_question


class _DenyUsage:
    def can_proceed(self, user_id: str, tier: str) -> bool:
        return False

    def record_usage(self, **kwargs):
        raise AssertionError("record_usage must not run when can_proceed is False")


def test_can_proceed_false_skips_llm_and_does_not_record():
    client = FakeLLMClient(text="isto nunca deve ser visto")
    answer = answer_educador_question(
        user_id="alice",
        tier="pro",
        question="O que é o spread?",
        client=client,
        usage=_DenyUsage(),  # type: ignore[arg-type]
        concept_id="spread",
    )
    assert client.calls == []
    assert answer.limit_reached is True
    assert answer.blocked is False
    assert answer.text == LIMIT_REACHED_TEXT
    assert answer.usage_id is None
    assert answer.input_tokens is None


def test_real_usage_service_denial_also_skips_client(tmp_path: Path):
    usage = UsageService(
        UsageRepository(tmp_path / "ai_usage.db"),
        quotas_path=_tiny_quotas(tmp_path),
    )
    usage.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=1_000_000,
        output_tokens=0,
    )
    client = FakeLLMClient()
    answer = answer_educador_question(
        user_id="alice",
        tier="free",
        question="O que é o spread?",
        client=client,
        usage=usage,
        concept_id="spread",
    )
    assert client.calls == []
    assert answer.limit_reached is True


def _tiny_quotas(tmp_path: Path) -> str:
    import json

    path = tmp_path / "quotas.json"
    path.write_text(
        json.dumps(
            {
                "tiers": {
                    "free": {"daily_cost_usd": 0.50, "monthly_cost_usd": 1.00},
                    "pro": {"daily_cost_usd": 5.00, "monthly_cost_usd": 50.00},
                },
                "global": {"daily_cost_usd": 20.00, "monthly_cost_usd": 200.00},
                "rate_limit": {"max_calls_per_minute": 10, "max_calls_per_hour": 60},
            }
        ),
        encoding="utf-8",
    )
    return str(path)

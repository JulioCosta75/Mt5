"""Shared fixtures for isolated ai_usage tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ai_usage.application.services import UsageService
from ai_usage.config import DEFAULT_PRICING_PATH
from ai_usage.infrastructure.repositories import UsageRepository
from ai_usage.tests.clock import FIXED_NOW


def _write(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.fixture
def tmp_svc(tmp_path: Path):
    def factory(
        *,
        quotas: dict | None = None,
        pricing_path: str = DEFAULT_PRICING_PATH,
        now: datetime = FIXED_NOW,
    ) -> UsageService:
        quotas_path = _write(
            tmp_path / "quotas.json",
            quotas
            or {
                "tiers": {
                    "free": {"daily_cost_usd": 0.01, "monthly_cost_usd": 0.05},
                    "pro": {"daily_cost_usd": 0.05, "monthly_cost_usd": 0.20},
                },
                "global": {"daily_cost_usd": 0.08, "monthly_cost_usd": 0.50},
                "rate_limit": {"max_calls_per_minute": 3, "max_calls_per_hour": 10},
            },
        )
        clock = {"value": now}

        def _clock() -> datetime:
            return clock["value"]

        svc = UsageService(
            UsageRepository(tmp_path / "ai_usage.db"),
            pricing_path=pricing_path,
            quotas_path=quotas_path,
            clock=_clock,
        )
        svc.clock_box = clock  # type: ignore[attr-defined]
        return svc

    return factory

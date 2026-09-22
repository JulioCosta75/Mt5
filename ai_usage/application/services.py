"""Usage, quota, global budget, rate limit, and model routing (no LLM calls)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from ai_usage.config import DEFAULT_PRICING_PATH, DEFAULT_QUOTAS_PATH
from ai_usage.domain.entities import AIUsageRecord
from ai_usage.domain.rules import (
    UsageValidationError,
    decimal_limit,
    estimate_cost_usd,
    load_pricing,
    load_quotas,
    normalize_tier,
    require_mode,
    require_model,
    require_token_count,
    require_user_id,
)
from ai_usage.infrastructure.repositories import UsageRepository, new_id

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_utc_day(now: datetime) -> datetime:
    now = now.astimezone(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def _start_of_utc_month(now: datetime) -> datetime:
    now = now.astimezone(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def route_model(requested: str | None = None) -> str:
    """Default Haiku. Sonnet only when the caller explicitly requests it."""
    if requested is None:
        return "haiku"
    raw = str(requested).strip().lower()
    if raw == "sonnet":
        return "sonnet"
    return "haiku"


class UsageService:
    """Fail-closed budget guard. Never calls a network or LLM API."""

    def __init__(
        self,
        repo: UsageRepository,
        *,
        pricing_path: str = DEFAULT_PRICING_PATH,
        quotas_path: str = DEFAULT_QUOTAS_PATH,
        clock: Clock | None = None,
    ):
        self.repo = repo
        self.pricing_path = pricing_path
        self.quotas_path = quotas_path
        self._clock = clock or _utcnow

    def _now(self) -> datetime:
        return self._clock()

    def _pricing(self) -> dict:
        try:
            return load_pricing(self.pricing_path)
        except (OSError, ValueError, UsageValidationError):
            return {}

    def _quotas(self) -> dict | None:
        try:
            return load_quotas(self.quotas_path)
        except (OSError, ValueError, UsageValidationError):
            return None

    def record_usage(
        self,
        *,
        user_id: str,
        mode: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        occurred_at: datetime | None = None,
    ) -> AIUsageRecord:
        user_id = require_user_id(user_id)
        mode = require_mode(mode)
        model = require_model(model)
        input_tokens = require_token_count(input_tokens, "input_tokens")
        output_tokens = require_token_count(output_tokens, "output_tokens")
        pricing = self._pricing()
        if model not in pricing:
            raise UsageValidationError("pricing table missing or unreadable; refuse to record.")
        cost = estimate_cost_usd(model, input_tokens, output_tokens, pricing)
        record = AIUsageRecord(
            id=new_id(),
            user_id=user_id,
            mode=mode,  # type: ignore[arg-type]
            model=model,  # type: ignore[arg-type]
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            occurred_at=occurred_at or self._now(),
        )
        return self.repo.insert(record)

    def list_for_user(self, user_id: str) -> list[AIUsageRecord]:
        return self.repo.list_for_user(require_user_id(user_id))

    def check_quota(self, user_id: str, tier: str) -> bool:
        """True if this user is still under the tier's daily and monthly ceilings."""
        try:
            user_id = require_user_id(user_id)
        except UsageValidationError:
            return False
        mapped = normalize_tier(tier)
        if mapped is None:
            return False
        quotas = self._quotas()
        if quotas is None:
            return False
        try:
            limits = quotas["tiers"][mapped]
            daily_limit = decimal_limit(limits["daily_cost_usd"])
            monthly_limit = decimal_limit(limits["monthly_cost_usd"])
        except (KeyError, TypeError, UsageValidationError):
            return False
        now = self._now()
        daily = self.repo.sum_cost_since(user_id=user_id, since=_start_of_utc_day(now))
        monthly = self.repo.sum_cost_since(user_id=user_id, since=_start_of_utc_month(now))
        if daily >= daily_limit:
            return False
        if monthly >= monthly_limit:
            return False
        return True

    def check_global_budget(self) -> bool:
        """True if the app-wide daily and monthly ceilings are still open.

        Independent of any user tier. Fails closed (denies) if the config is
        missing or the ceiling is already reached.
        """
        quotas = self._quotas()
        if quotas is None:
            return False
        try:
            limits = quotas["global"]
            daily_limit = decimal_limit(limits["daily_cost_usd"])
            monthly_limit = decimal_limit(limits["monthly_cost_usd"])
        except (KeyError, TypeError, UsageValidationError):
            return False
        now = self._now()
        daily = self.repo.sum_cost_since(since=_start_of_utc_day(now))
        monthly = self.repo.sum_cost_since(since=_start_of_utc_month(now))
        if daily >= daily_limit:
            return False
        if monthly >= monthly_limit:
            return False
        return True

    def check_rate_limit(self, user_id: str) -> bool:
        """True if this user is under the per-minute and per-hour call caps."""
        try:
            user_id = require_user_id(user_id)
        except UsageValidationError:
            return False
        quotas = self._quotas()
        if quotas is None:
            return False
        try:
            limits = quotas["rate_limit"]
            per_minute = int(limits["max_calls_per_minute"])
            per_hour = int(limits["max_calls_per_hour"])
        except (KeyError, TypeError, ValueError):
            return False
        now = self._now()
        minute_count = self.repo.count_since(user_id=user_id, since=now - timedelta(seconds=60))
        hour_count = self.repo.count_since(user_id=user_id, since=now - timedelta(seconds=3600))
        if minute_count >= per_minute:
            return False
        if hour_count >= per_hour:
            return False
        return True

    def can_proceed(self, user_id: str, tier: str) -> bool:
        """Fail-closed conjunction of rate limit, per-user quota, and global budget."""
        return (
            self.check_rate_limit(user_id)
            and self.check_quota(user_id, tier)
            and self.check_global_budget()
        )

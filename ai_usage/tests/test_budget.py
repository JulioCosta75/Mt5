"""App-wide ceiling denies even when the user's own quota still has room."""

from __future__ import annotations

from ai_usage.tests.clock import FIXED_NOW


def _haiku_input_costing(svc, user: str, usd: float) -> None:
    tokens = int(round(usd * 1_000_000))
    svc.record_usage(
        user_id=user,
        mode="educador",
        model="haiku",
        input_tokens=tokens,
        output_tokens=0,
        occurred_at=FIXED_NOW,
    )


def test_global_budget_open_when_empty(tmp_svc):
    svc = tmp_svc()
    assert svc.check_global_budget() is True


def test_global_budget_denies_even_when_user_quota_would_allow(tmp_svc):
    svc = tmp_svc(
        quotas={
            "tiers": {
                "free": {"daily_cost_usd": 1.00, "monthly_cost_usd": 5.00},
                "pro": {"daily_cost_usd": 5.00, "monthly_cost_usd": 50.00},
            },
            "global": {"daily_cost_usd": 0.01, "monthly_cost_usd": 1.00},
            "rate_limit": {"max_calls_per_minute": 100, "max_calls_per_hour": 1000},
        }
    )
    _haiku_input_costing(svc, "bob", 0.01)
    assert svc.check_quota("alice", "pro") is True
    assert svc.check_global_budget() is False
    assert svc.can_proceed("alice", "pro") is False


def test_missing_quotas_file_fails_closed(tmp_svc, tmp_path):
    svc = tmp_svc()
    svc.quotas_path = str(tmp_path / "does-not-exist.json")
    assert svc.check_global_budget() is False
    assert svc.check_quota("alice", "pro") is False
    assert svc.check_rate_limit("alice") is False

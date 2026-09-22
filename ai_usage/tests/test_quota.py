"""Free and Pro per-user daily/monthly ceilings."""

from __future__ import annotations

from ai_usage.tests.clock import FIXED_NOW


def _haiku_input_costing(svc, user: str, usd: float) -> None:
    """Record one Haiku call whose input tokens cost exactly ``usd`` dollars."""
    # $1 / million input tokens → tokens = usd * 1_000_000
    tokens = int(round(usd * 1_000_000))
    svc.record_usage(
        user_id=user,
        mode="educador",
        model="haiku",
        input_tokens=tokens,
        output_tokens=0,
        occurred_at=FIXED_NOW,
    )


def test_free_tier_allowed_before_daily_limit(tmp_svc):
    svc = tmp_svc()
    _haiku_input_costing(svc, "alice", 0.009)
    assert svc.check_quota("alice", "free") is True


def test_free_tier_blocked_after_daily_limit(tmp_svc):
    svc = tmp_svc()
    _haiku_input_costing(svc, "alice", 0.01)
    assert svc.check_quota("alice", "free") is False


def test_pro_tier_still_allowed_when_free_would_be_blocked(tmp_svc):
    svc = tmp_svc()
    _haiku_input_costing(svc, "alice", 0.01)
    assert svc.check_quota("alice", "free") is False
    assert svc.check_quota("alice", "pro") is True


def test_pro_tier_blocked_after_its_daily_limit(tmp_svc):
    svc = tmp_svc()
    _haiku_input_costing(svc, "alice", 0.05)
    assert svc.check_quota("alice", "pro") is False


def test_pro_active_alias_uses_pro_limits(tmp_svc):
    svc = tmp_svc()
    _haiku_input_costing(svc, "alice", 0.01)
    assert svc.check_quota("alice", "pro_active") is True
    _haiku_input_costing(svc, "alice", 0.04)
    assert svc.check_quota("alice", "pro_active") is False


def test_unknown_tier_fails_closed(tmp_svc):
    svc = tmp_svc()
    assert svc.check_quota("alice", "enterprise") is False
    assert svc.check_quota("alice", "") is False


def test_empty_user_fails_closed(tmp_svc):
    svc = tmp_svc()
    assert svc.check_quota("", "pro") is False

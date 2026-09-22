"""Per-user call caps, separate from daily cost quota."""

from __future__ import annotations

from datetime import timedelta

from ai_usage.tests.clock import FIXED_NOW


def test_rate_limit_blocks_after_max_calls_per_minute(tmp_svc):
    svc = tmp_svc()
    for _ in range(3):
        svc.record_usage(
            user_id="alice",
            mode="educador",
            model="haiku",
            input_tokens=1,
            output_tokens=0,
            occurred_at=FIXED_NOW,
        )
    assert svc.check_rate_limit("alice") is False
    assert svc.check_rate_limit("bob") is True


def test_rate_limit_resets_after_one_minute(tmp_svc):
    svc = tmp_svc()
    for _ in range(3):
        svc.record_usage(
            user_id="alice",
            mode="educador",
            model="haiku",
            input_tokens=1,
            output_tokens=0,
            occurred_at=FIXED_NOW,
        )
    assert svc.check_rate_limit("alice") is False
    svc.clock_box["value"] = FIXED_NOW + timedelta(seconds=61)
    assert svc.check_rate_limit("alice") is True

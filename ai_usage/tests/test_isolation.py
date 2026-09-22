"""Per-user rows never leak to another user."""

from __future__ import annotations

from ai_usage.tests.clock import FIXED_NOW


def test_list_for_user_never_returns_another_users_rows(tmp_svc):
    svc = tmp_svc()
    alice = svc.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=1000,
        output_tokens=0,
        occurred_at=FIXED_NOW,
    )
    bob = svc.record_usage(
        user_id="bob",
        mode="conta",
        model="sonnet",
        input_tokens=2000,
        output_tokens=10,
        occurred_at=FIXED_NOW,
    )
    alice_rows = svc.list_for_user("alice")
    bob_rows = svc.list_for_user("bob")
    assert [row.id for row in alice_rows] == [alice.id]
    assert [row.id for row in bob_rows] == [bob.id]
    assert all(row.user_id == "alice" for row in alice_rows)
    assert all(row.user_id == "bob" for row in bob_rows)


def test_quota_uses_only_that_users_spend(tmp_svc):
    svc = tmp_svc()
    svc.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=10_000,
        output_tokens=0,
        occurred_at=FIXED_NOW,
    )
    assert svc.check_quota("alice", "free") is False
    assert svc.check_quota("bob", "free") is True

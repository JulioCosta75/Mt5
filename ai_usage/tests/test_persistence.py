"""Append-only ledger: insert and list, never update or delete."""

from __future__ import annotations

from ai_usage.infrastructure.repositories import UsageRepository
from ai_usage.tests.clock import FIXED_NOW


def test_repository_has_no_update_or_delete_helpers():
    names = {name for name in dir(UsageRepository) if not name.startswith("_")}
    lowered = {name.lower() for name in names}
    assert "update" not in lowered
    assert "delete" not in lowered
    assert "insert" in names
    assert "list_for_user" in names


def test_recorded_row_survives_further_inserts_unchanged(tmp_svc):
    svc = tmp_svc()
    first = svc.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=100,
        output_tokens=10,
        occurred_at=FIXED_NOW,
    )
    svc.record_usage(
        user_id="alice",
        mode="comunicador",
        model="sonnet",
        input_tokens=50,
        output_tokens=5,
        occurred_at=FIXED_NOW,
    )
    rows = svc.list_for_user("alice")
    assert rows[0].id == first.id
    assert rows[0].input_tokens == 100
    assert rows[0].mode == "educador"
    assert len(rows) == 2

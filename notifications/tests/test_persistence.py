"""SQLite round-trip and additive schema."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from notifications.application.services import PreferenceService
from notifications.infrastructure.repositories import NotificationPreferenceRepository


SCHEMA = (
    Path(__file__).resolve().parents[1] / "infrastructure" / "schema.sql"
).read_text(encoding="utf-8")


def test_schema_is_additive_only():
    lowered = SCHEMA.lower()
    assert "create table if not exists" in lowered
    assert "drop table" not in lowered
    assert "drop column" not in lowered
    assert "truncate" not in lowered


def test_round_trip_and_audit():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "notifications.db"
        repo = NotificationPreferenceRepository(db)
        assert repo.schema_version() == 1
        svc = PreferenceService(repo)
        created = svc.create(
            actor="alice",
            user_id="alice",
            account_id="MT5-4444",
            alert_type="periodic_report",
            priority="low",
            frequency="digest",
            channel="email",
            quiet_hours_start="23:00",
            quiet_hours_end="06:30",
        )
        assert created.active is False
        assert isinstance(created.id, UUID)

        again = NotificationPreferenceRepository(db)
        loaded = again.list_preferences("alice", "MT5-4444")
        assert len(loaded) == 1
        row = loaded[0]
        assert row.id == created.id
        assert row.alert_type == "periodic_report"
        assert row.frequency == "digest"
        assert row.channel == "email"
        assert row.quiet_hours_start == "23:00"
        assert row.quiet_hours_end == "06:30"
        assert row.active is False

        updated = svc.update(
            actor="alice",
            user_id="alice",
            account_id="MT5-4444",
            preference_id=created.id,
            frequency="immediate",
            active=True,
        )
        assert updated.frequency == "immediate"
        assert updated.active is True

        audit = again.list_audit("alice", "MT5-4444", created.id)
        fields = {(e.action, e.field, e.old_value, e.new_value) for e in audit}
        assert ("create", "alert_type", None, "periodic_report") in fields
        assert ("update", "frequency", "digest", "immediate") in fields
        assert ("update", "active", "false", "true") in fields

        svc.delete(
            actor="alice",
            user_id="alice",
            account_id="MT5-4444",
            preference_id=created.id,
        )
        assert again.list_preferences("alice", "MT5-4444") == []
        after_delete = again.list_audit("alice", "MT5-4444", created.id)
        assert any(e.action == "delete" for e in after_delete)
        assert again.list_audit("bob", "MT5-4444", created.id) == []

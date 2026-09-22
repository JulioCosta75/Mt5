"""Create / update / delete notification preferences with append-only audit."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from notifications.domain.entities import (
    NotificationPreference,
    NotificationPreferenceAuditEntry,
)
from notifications.domain.rules import validate_preference
from notifications.infrastructure.repositories import (
    NotificationPreferenceRepository,
    PreferenceNotFoundError,
    new_id,
)

_AUDIT_FIELDS = (
    "alert_type",
    "priority",
    "frequency",
    "channel",
    "quiet_hours_start",
    "quiet_hours_end",
    "active",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _field_value(pref: NotificationPreference, field: str) -> str | None:
    value = getattr(pref, field)
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


class PreferenceService:
    """Consent-preserving writes. No bulk-enable. No default-on rows."""

    def __init__(self, repo: NotificationPreferenceRepository):
        self.repo = repo

    def create(
        self,
        *,
        actor: str,
        user_id: str,
        account_id: str,
        alert_type: str,
        priority: str,
        frequency: str,
        channel: str,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
        active: bool = False,
    ) -> NotificationPreference:
        pref = NotificationPreference(
            id=new_id(),
            user_id=user_id,
            account_id=account_id,
            alert_type=alert_type,  # type: ignore[arg-type]
            priority=priority,  # type: ignore[arg-type]
            frequency=frequency,  # type: ignore[arg-type]
            channel=channel,  # type: ignore[arg-type]
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            active=bool(active),
        )
        pref = validate_preference(pref)
        saved = self.repo.save_preference(pref)
        self._audit_snapshot(saved, actor=actor, action="create", previous=None)
        return saved

    def list_for_account(
        self, user_id: str, account_id: str
    ) -> list[NotificationPreference]:
        from notifications.domain.rules import require_account_id, require_user_id

        return self.repo.list_preferences(
            require_user_id(user_id), require_account_id(account_id)
        )

    def update(
        self,
        *,
        actor: str,
        user_id: str,
        account_id: str,
        preference_id: UUID,
        **changes: object,
    ) -> NotificationPreference:
        existing = self.repo.get_preference(user_id, account_id, preference_id)
        if existing is None:
            raise PreferenceNotFoundError(
                "No preference matching this user_id, account_id, and id."
            )
        working = replace(existing)
        for key, value in changes.items():
            if key not in _AUDIT_FIELDS:
                continue
            setattr(working, key, value)
        working = validate_preference(working)
        saved = self.repo.update_preference(working)
        self._audit_snapshot(saved, actor=actor, action="update", previous=existing)
        return saved

    def delete(
        self,
        *,
        actor: str,
        user_id: str,
        account_id: str,
        preference_id: UUID,
    ) -> None:
        existing = self.repo.get_preference(user_id, account_id, preference_id)
        if existing is None:
            raise PreferenceNotFoundError(
                "No preference matching this user_id, account_id, and id."
            )
        self.repo.delete_preference(user_id, account_id, preference_id)
        self._audit_snapshot(existing, actor=actor, action="delete", previous=existing)

    def _audit_snapshot(
        self,
        pref: NotificationPreference,
        *,
        actor: str,
        action: str,
        previous: NotificationPreference | None,
    ) -> None:
        now = _utcnow()
        for field in _AUDIT_FIELDS:
            old = _field_value(previous, field) if previous is not None else None
            new = _field_value(pref, field) if action != "delete" else None
            if action == "update" and old == new:
                continue
            if action == "delete":
                new = None
                old = _field_value(pref, field)
            self.repo.append_audit(
                NotificationPreferenceAuditEntry(
                    id=new_id(),
                    preference_id=pref.id,
                    user_id=pref.user_id,
                    account_id=pref.account_id,
                    actor=actor,
                    action=action,  # type: ignore[arg-type]
                    field=field,
                    old_value=old,
                    new_value=new,
                    occurred_at=now,
                )
            )

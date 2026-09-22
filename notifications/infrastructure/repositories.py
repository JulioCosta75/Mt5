"""SQLite persistence for notifications — notifications.db only."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from notifications.domain.entities import (
    NotificationPreference,
    NotificationPreferenceAuditEntry,
)
from notifications.domain.rules import PreferenceValidationError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class PreferenceNotFoundError(LookupError):
    """No preference for this (user_id, account_id, id) combination."""


class NotificationPreferenceRepository:
    """SQLite repository isolated from atlas.db and knowledge.db."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        cx = sqlite3.connect(self.db_path)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA foreign_keys = ON")
        return cx

    @contextmanager
    def _connection(self):
        cx = self._connect()
        try:
            with cx:
                yield cx
        finally:
            cx.close()

    def _init_schema(self) -> None:
        schema_file = Path(__file__).with_name("schema.sql")
        ddl = schema_file.read_text(encoding="utf-8")
        with self._connection() as cx:
            cx.executescript(ddl)

    def schema_version(self) -> int:
        with self._connection() as cx:
            row = cx.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'",
            ).fetchone()
        return int(row["value"]) if row else 1

    def save_preference(self, pref: NotificationPreference) -> NotificationPreference:
        now = _utcnow()
        if pref.created_at is None:
            pref.created_at = now
        pref.updated_at = now
        with self._connection() as cx:
            try:
                cx.execute(
                    """
                    INSERT INTO notification_preferences (
                        id, user_id, account_id, alert_type, priority, frequency,
                        channel, quiet_hours_start, quiet_hours_end, active,
                        created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(pref.id),
                        pref.user_id,
                        pref.account_id,
                        pref.alert_type,
                        pref.priority,
                        pref.frequency,
                        pref.channel,
                        pref.quiet_hours_start,
                        pref.quiet_hours_end,
                        1 if pref.active else 0,
                        _iso(pref.created_at),
                        _iso(pref.updated_at),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise PreferenceValidationError(
                    "A preference for this user, account, alert_type, and channel already exists."
                ) from exc
        return pref

    def update_preference(self, pref: NotificationPreference) -> NotificationPreference:
        pref.updated_at = _utcnow()
        with self._connection() as cx:
            cur = cx.execute(
                """
                UPDATE notification_preferences
                   SET alert_type = ?,
                       priority = ?,
                       frequency = ?,
                       channel = ?,
                       quiet_hours_start = ?,
                       quiet_hours_end = ?,
                       active = ?,
                       updated_at = ?
                 WHERE id = ? AND user_id = ? AND account_id = ?
                """,
                (
                    pref.alert_type,
                    pref.priority,
                    pref.frequency,
                    pref.channel,
                    pref.quiet_hours_start,
                    pref.quiet_hours_end,
                    1 if pref.active else 0,
                    _iso(pref.updated_at),
                    str(pref.id),
                    pref.user_id,
                    pref.account_id,
                ),
            )
            if cur.rowcount != 1:
                raise PreferenceNotFoundError(
                    "No preference matching this user_id, account_id, and id."
                )
        return pref

    def get_preference(
        self, user_id: str, account_id: str, preference_id: UUID
    ) -> NotificationPreference | None:
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT * FROM notification_preferences
                 WHERE id = ? AND user_id = ? AND account_id = ?
                """,
                (str(preference_id), user_id, account_id),
            ).fetchone()
        if not row:
            return None
        return self._row_to_preference(row)

    def list_preferences(
        self, user_id: str, account_id: str
    ) -> list[NotificationPreference]:
        """List one user's preferences for one account. Never cross-tenant."""
        with self._connection() as cx:
            rows = cx.execute(
                """
                SELECT * FROM notification_preferences
                 WHERE user_id = ? AND account_id = ?
                 ORDER BY alert_type ASC, channel ASC
                """,
                (user_id, account_id),
            ).fetchall()
        return [self._row_to_preference(r) for r in rows]

    def delete_preference(
        self, user_id: str, account_id: str, preference_id: UUID
    ) -> None:
        with self._connection() as cx:
            cur = cx.execute(
                """
                DELETE FROM notification_preferences
                 WHERE id = ? AND user_id = ? AND account_id = ?
                """,
                (str(preference_id), user_id, account_id),
            )
            if cur.rowcount != 1:
                raise PreferenceNotFoundError(
                    "No preference matching this user_id, account_id, and id."
                )

    def append_audit(
        self, entry: NotificationPreferenceAuditEntry
    ) -> NotificationPreferenceAuditEntry:
        with self._connection() as cx:
            cx.execute(
                """
                INSERT INTO notification_preference_audit (
                    id, preference_id, user_id, account_id, actor, action,
                    field, old_value, new_value, occurred_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(entry.id),
                    str(entry.preference_id),
                    entry.user_id,
                    entry.account_id,
                    entry.actor,
                    entry.action,
                    entry.field,
                    entry.old_value,
                    entry.new_value,
                    _iso(entry.occurred_at),
                ),
            )
        return entry

    def list_audit(
        self, user_id: str, account_id: str, preference_id: UUID | None = None
    ) -> list[NotificationPreferenceAuditEntry]:
        sql = """
            SELECT * FROM notification_preference_audit
             WHERE user_id = ? AND account_id = ?
        """
        params: list[object] = [user_id, account_id]
        if preference_id is not None:
            sql += " AND preference_id = ?"
            params.append(str(preference_id))
        sql += " ORDER BY occurred_at ASC"
        with self._connection() as cx:
            rows = cx.execute(sql, params).fetchall()
        return [self._row_to_audit(r) for r in rows]

    @staticmethod
    def _row_to_preference(row: sqlite3.Row) -> NotificationPreference:
        return NotificationPreference(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            account_id=row["account_id"],
            alert_type=row["alert_type"],
            priority=row["priority"],
            frequency=row["frequency"],
            channel=row["channel"],
            quiet_hours_start=row["quiet_hours_start"],
            quiet_hours_end=row["quiet_hours_end"],
            active=bool(row["active"]),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    @staticmethod
    def _row_to_audit(row: sqlite3.Row) -> NotificationPreferenceAuditEntry:
        return NotificationPreferenceAuditEntry(
            id=UUID(row["id"]),
            preference_id=UUID(row["preference_id"]),
            user_id=row["user_id"],
            account_id=row["account_id"],
            actor=row["actor"],
            action=row["action"],
            field=row["field"],
            old_value=row["old_value"],
            new_value=row["new_value"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
        )


def new_id() -> UUID:
    return uuid4()

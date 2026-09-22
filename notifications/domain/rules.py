"""Validation and consent rules for notification preferences."""

from __future__ import annotations

import re

from notifications.domain.entities import (
    ALERT_TYPES,
    CHANNEL_LABELS,
    FREQUENCIES,
    PRIORITIES,
    NotificationPreference,
)

_ACCOUNT_ID = re.compile(r"^MT5-\d+$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class PreferenceValidationError(ValueError):
    """Raised when a preference field is invalid. Never silently accepted."""


def require_user_id(user_id: str) -> str:
    raw = (user_id or "").strip()
    if not raw:
        raise PreferenceValidationError("user_id is required.")
    return raw


def require_account_id(account_id: str) -> str:
    raw = (account_id or "").strip()
    if not raw:
        raise PreferenceValidationError("account_id is required.")
    if not _ACCOUNT_ID.fullmatch(raw):
        raise PreferenceValidationError(
            "account_id must use the MT5-{login} format (e.g. MT5-5609382)."
        )
    return raw


def require_alert_type(alert_type: str) -> str:
    raw = (alert_type or "").strip()
    if raw not in ALERT_TYPES:
        allowed = ", ".join(sorted(ALERT_TYPES))
        raise PreferenceValidationError(
            f"unknown alert_type {alert_type!r}; allowed: {allowed}."
        )
    return raw


def require_frequency(frequency: str) -> str:
    raw = (frequency or "").strip()
    if raw not in FREQUENCIES:
        allowed = ", ".join(sorted(FREQUENCIES))
        raise PreferenceValidationError(
            f"invalid frequency {frequency!r}; allowed: {allowed}."
        )
    return raw


def require_priority(priority: str) -> str:
    raw = (priority or "").strip()
    if raw not in PRIORITIES:
        allowed = ", ".join(sorted(PRIORITIES))
        raise PreferenceValidationError(
            f"invalid priority {priority!r}; allowed: {allowed}."
        )
    return raw


def require_channel(channel: str) -> str:
    raw = (channel or "").strip()
    if raw not in CHANNEL_LABELS:
        allowed = ", ".join(sorted(CHANNEL_LABELS))
        raise PreferenceValidationError(
            f"unknown channel label {channel!r}; allowed: {allowed}."
        )
    return raw


def require_quiet_hours(
    start: str | None, end: str | None
) -> tuple[str | None, str | None]:
    start_raw = (start or "").strip() or None
    end_raw = (end or "").strip() or None
    if start_raw is None and end_raw is None:
        return None, None
    if start_raw is None or end_raw is None:
        raise PreferenceValidationError(
            "quiet_hours_start and quiet_hours_end must both be set or both omitted."
        )
    if _HHMM.fullmatch(start_raw) is None:
        raise PreferenceValidationError(
            f"malformed quiet_hours_start {start!r}; expected HH:MM (00:00–23:59)."
        )
    if _HHMM.fullmatch(end_raw) is None:
        raise PreferenceValidationError(
            f"malformed quiet_hours_end {end!r}; expected HH:MM (00:00–23:59)."
        )
    return start_raw, end_raw


def validate_preference(pref: NotificationPreference) -> NotificationPreference:
    pref.user_id = require_user_id(pref.user_id)
    pref.account_id = require_account_id(pref.account_id)
    pref.alert_type = require_alert_type(pref.alert_type)  # type: ignore[assignment]
    pref.priority = require_priority(pref.priority)  # type: ignore[assignment]
    pref.frequency = require_frequency(pref.frequency)  # type: ignore[assignment]
    pref.channel = require_channel(pref.channel)  # type: ignore[assignment]
    pref.quiet_hours_start, pref.quiet_hours_end = require_quiet_hours(
        pref.quiet_hours_start, pref.quiet_hours_end
    )
    pref.active = bool(pref.active)
    return pref

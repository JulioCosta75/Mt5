"""Domain entities for notification preferences and consent (Stage 1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

AlertType = Literal[
    "risk_drawdown",
    "account_change",
    "ea_status",
    "technical_failure",
    "periodic_report",
    "new_knowledge",
]

Frequency = Literal["immediate", "digest"]
Priority = Literal["critical", "high", "normal", "low"]
ChannelLabel = Literal["telegram", "email", "push"]
AuditAction = Literal["create", "update", "delete"]

ALERT_TYPES: frozenset[str] = frozenset({
    "risk_drawdown",
    "account_change",
    "ea_status",
    "technical_failure",
    "periodic_report",
    "new_knowledge",
})
FREQUENCIES: frozenset[str] = frozenset({"immediate", "digest"})
PRIORITIES: frozenset[str] = frozenset({"critical", "high", "normal", "low"})
CHANNEL_LABELS: frozenset[str] = frozenset({"telegram", "email", "push"})


@dataclass
class NotificationPreference:
    """Explicit user consent to receive one alert type on one account.

    ``active`` defaults to False. A row exists only because a user created it.
    ``channel`` is an abstract label — no chat_id, email, or linking identity.
    ``account_id`` uses the Phase 2 / Gate 5 ``MT5-{login}`` format.
    """

    id: UUID
    user_id: str
    account_id: str
    alert_type: AlertType
    priority: Priority
    frequency: Frequency
    channel: ChannelLabel
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    active: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class NotificationPreferenceAuditEntry:
    """Append-only record of a preference create, update, or delete."""

    id: UUID
    preference_id: UUID
    user_id: str
    account_id: str
    actor: str
    action: AuditAction
    field: str
    old_value: str | None
    new_value: str | None
    occurred_at: datetime

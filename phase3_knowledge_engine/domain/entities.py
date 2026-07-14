"""Domain entities for the Phase 3 Knowledge Management Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID


EvidenceType = Literal["trade", "backtest_run", "incident", "metric_snapshot"]
AccountType = Literal["demo", "live"]
TestType = Literal["forward", "backtest", "paper"]
EAStatus = Literal["active", "restricted", "stopped", "testing"]
EvidenceImpact = Literal["confirm", "weaken", "review", "invalidate"]


@dataclass
class MarketContext:
    """Contextual envelope around an observation or piece of evidence."""

    session: str | None = None
    market_regime: str | None = None
    volatility: float | None = None
    spread: float | None = None
    symbol: str | None = None
    occurred_at: datetime | None = None
    weekday: str | None = None
    notes: str | None = None


@dataclass
class EvidenceItem:
    """Atomic evidence linked to conclusions — never promoted alone to knowledge."""

    id: UUID
    ea_profile_id: UUID
    evidence_type: EvidenceType
    occurred_at: datetime
    symbol: str
    session: str | None = None
    market_regime: str | None = None
    volatility: float | None = None
    spread: float | None = None
    pnl: float | None = None
    drawdown: float | None = None
    entry_reason: str | None = None
    exit_reason: str | None = None
    ea_version: str | None = None
    account_type: AccountType | None = None
    test_type: TestType | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    context: MarketContext | None = None


@dataclass
class PerformanceMetrics:
    period_start: date
    period_end: date
    net_pnl: float
    max_drawdown_pct: float
    win_rate: float | None = None
    trade_count: int = 0
    sharpe: float | None = None


@dataclass
class ChangeLogEntry:
    changed_at: datetime
    from_version: str
    to_version: str
    description: str
    effect_summary: str | None = None


@dataclass
class EAKnowledgeProfile:
    """Living dossier for an Expert Advisor."""

    id: UUID
    ea_key: str
    name: str
    version: str
    purpose: str
    entry_rules: str
    exit_rules: str
    risk_rules: dict[str, Any]
    permitted_symbols: list[str]
    permitted_sessions: list[str]
    market_conditions: dict[str, Any]
    status: EAStatus = "testing"
    known_strengths: list[str] = field(default_factory=list)
    known_weaknesses: list[str] = field(default_factory=list)
    open_hypotheses: list[str] = field(default_factory=list)
    validated_conclusions: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class KnowledgeRecord:
    """A knowledge statement moving through the validation lifecycle."""

    id: UUID
    ea_profile_id: UUID
    validation_state: str
    statement: str
    evidence_count: int = 0
    sample_size: int = 0
    date_range_start: date | None = None
    date_range_end: date | None = None
    confidence_score: float = 0.0
    supporting_evidence_ids: list[UUID] = field(default_factory=list)
    contradictory_evidence_ids: list[UUID] = field(default_factory=list)
    last_reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    relevance_for_decisions: str | None = None
    context_documented: bool = False
    material_contradictions_resolved: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class AuditTrailEntry:
    """Immutable record of a validation-state transition."""

    id: UUID
    knowledge_record_id: UUID
    from_state: str
    to_state: str
    transitioned_at: datetime
    actor: str
    justification: str
    evidence_ids: list[UUID] = field(default_factory=list)


@dataclass
class EvidenceImpactRecord:
    """How new evidence affected existing knowledge without silent rewrite."""

    id: UUID
    knowledge_record_id: UUID
    evidence_id: UUID
    impact: EvidenceImpact
    recorded_at: datetime
    actor: str
    notes: str

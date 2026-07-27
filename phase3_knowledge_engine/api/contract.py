"""API contract models for future Phase 3 HTTP surface.

NOT mounted on backend/server.py. Reference only until integration gate.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MarketContextDTO(BaseModel):
    session: str | None = None
    market_regime: str | None = None
    volatility: float | None = None
    spread: float | None = None
    symbol: str | None = None
    occurred_at: datetime | None = None


class EAProfileDTO(BaseModel):
    id: UUID | None = None
    ea_key: str
    name: str
    version: str
    purpose: str
    entry_rules: str
    exit_rules: str
    risk_rules: dict[str, Any] = Field(default_factory=dict)
    permitted_symbols: list[str] = Field(default_factory=list)
    permitted_sessions: list[str] = Field(default_factory=list)
    market_conditions: dict[str, Any] = Field(default_factory=dict)
    status: Literal["active", "restricted", "stopped", "testing"] = "testing"


class EvidenceDTO(BaseModel):
    id: UUID | None = None
    ea_profile_id: UUID
    evidence_type: Literal["trade", "backtest_run", "incident", "metric_snapshot"]
    occurred_at: datetime
    symbol: str
    session: str | None = None
    market_regime: str | None = None
    pnl: float | None = None
    drawdown: float | None = None
    ea_version: str | None = None
    account_type: Literal["demo", "live"] | None = None
    context: MarketContextDTO | None = None


class KnowledgeRecordDTO(BaseModel):
    id: UUID
    ea_profile_id: UUID
    validation_state: str
    statement: str
    evidence_count: int
    sample_size: int
    confidence_score: float
    date_range_start: date | None = None
    date_range_end: date | None = None


class TransitionRequestDTO(BaseModel):
    to_state: str
    actor: str
    justification: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    relevance_for_decisions: str | None = None
    context_documented: bool = False
    material_contradictions_resolved: bool = False


class AuditTrailDTO(BaseModel):
    from_state: str
    to_state: str
    transitioned_at: datetime
    actor: str
    justification: str
    evidence_ids: list[UUID] = Field(default_factory=list)


# Future routes (disabled):
# GET    /api/knowledge/v1/ea-profiles
# GET    /api/knowledge/v1/ea-profiles/{id}
# POST   /api/knowledge/v1/ea-profiles
# POST   /api/knowledge/v1/observations
# POST   /api/knowledge/v1/records/{id}/hypothesis
# POST   /api/knowledge/v1/records/{id}/transition
# GET    /api/knowledge/v1/records/{id}/audit
# GET    /api/knowledge/v1/query/best-session?ea_key=...

API_PREFIX = "/api/knowledge/v1"
FEATURE_FLAG_ENV = "PHASE3_KNOWLEDGE_ENGINE_ENABLED"

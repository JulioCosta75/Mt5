"""Domain entities for isolated AI usage accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

Mode = Literal["educador", "conta", "comunicador"]
ModelName = Literal["haiku", "sonnet"]
Tier = Literal["free", "pro"]

MODES: frozenset[str] = frozenset({"educador", "conta", "comunicador"})
MODELS: frozenset[str] = frozenset({"haiku", "sonnet"})
TIERS: frozenset[str] = frozenset({"free", "pro"})

# Public `tier` field from backend/license.py public_state() is "pro" or "free".
# Internal license status names map onto that without importing license.py.
LICENSE_TIER_ALIASES: dict[str, str] = {
    "free": "free",
    "pro": "pro",
    "pro_active": "pro",
    "pro_expired": "free",
    "checking": "free",
}


@dataclass(frozen=True)
class AIUsageRecord:
    """Append-only record of one synthetic or future live AI call."""

    id: UUID
    user_id: str
    mode: Mode
    model: ModelName
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    occurred_at: datetime

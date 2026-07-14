"""Evidence source port — contract for future MT5/backtest ingestion."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from phase3_knowledge_engine.domain.entities import EvidenceItem


@runtime_checkable
class EvidenceSourcePort(Protocol):
    """Read-only adapter contract: external system → EvidenceItem."""

    @property
    def source_system(self) -> str:
        """Stable identifier for provenance (e.g. mt5_bridge, backtest_export)."""
        ...

    def fetch_pending(
        self,
        *,
        ea_profile_id: UUID | None = None,
        limit: int = 100,
    ) -> list[EvidenceItem]:
        """Return evidence not yet ingested; empty when nothing pending."""
        ...

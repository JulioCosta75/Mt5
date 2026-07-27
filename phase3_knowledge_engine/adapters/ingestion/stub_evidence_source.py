"""Stub evidence source — satisfies EvidenceSourcePort without external integration."""

from __future__ import annotations

from uuid import UUID

from phase3_knowledge_engine.domain.entities import EvidenceItem


class StubEvidenceSource:
    """Placeholder adapter for Gate 1 ingestion. Returns no pending evidence."""

    @property
    def source_system(self) -> str:
        return "stub"

    def fetch_pending(
        self,
        *,
        ea_profile_id: UUID | None = None,
        limit: int = 100,
    ) -> list[EvidenceItem]:
        return []

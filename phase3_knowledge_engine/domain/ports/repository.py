"""Repository port — persistence only, no business-rule decisions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    EvidenceImpactRecord,
    EvidenceItem,
    KnowledgeRecord,
)


@runtime_checkable
class KnowledgeRepositoryPort(Protocol):
    """Persistence contract for the Knowledge Engine."""

    def save_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile: ...

    def get_ea_profile(self, profile_id: UUID) -> EAKnowledgeProfile | None: ...

    def save_evidence(self, item: EvidenceItem) -> EvidenceItem: ...

    def count_observations_for_ea(self, ea_profile_id: UUID) -> int: ...

    def save_knowledge_record(self, record: KnowledgeRecord) -> KnowledgeRecord: ...

    def get_knowledge_record(self, record_id: UUID) -> KnowledgeRecord | None: ...

    def append_audit(self, entry: AuditTrailEntry) -> AuditTrailEntry: ...

    def list_audit_trail(self, knowledge_record_id: UUID) -> list[AuditTrailEntry]: ...

    def append_evidence_impact(self, impact: EvidenceImpactRecord) -> EvidenceImpactRecord: ...

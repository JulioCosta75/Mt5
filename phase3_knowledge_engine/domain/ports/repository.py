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
from phase3_knowledge_engine.domain.validation_states import ValidationState


@runtime_checkable
class KnowledgeRepositoryPort(Protocol):
    """Persistence contract for the Knowledge Engine."""

    def save_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile: ...

    def get_ea_profile(self, profile_id: UUID) -> EAKnowledgeProfile | None: ...

    def get_ea_profile_by_ea_key(self, ea_key: str) -> EAKnowledgeProfile | None: ...

    def save_evidence(self, item: EvidenceItem) -> EvidenceItem: ...

    def has_evidence_by_external_id(
        self, source_system: str, external_id: str
    ) -> bool: ...

    def get_evidence_by_external_id(
        self, source_system: str, external_id: str
    ) -> EvidenceItem | None: ...

    def count_observations_for_ea(self, ea_profile_id: UUID) -> int: ...

    def save_knowledge_record(self, record: KnowledgeRecord) -> KnowledgeRecord: ...

    def get_knowledge_record(self, record_id: UUID) -> KnowledgeRecord | None: ...

    def find_knowledge_record_by_signature(
        self, context_signature: str
    ) -> KnowledgeRecord | None:
        """Pre-hypothesis only: RAW_OBSERVATION or REPEATED_PATTERN."""
        ...

    def find_post_hypothesis_record_by_signature(
        self, context_signature: str
    ) -> KnowledgeRecord | None:
        """HYPOTHESIS or later — for evidence-impact routing, not grouping."""
        ...

    def list_knowledge_records_by_state(
        self,
        validation_state: ValidationState,
        ea_profile_id: UUID | None = None,
        limit: int = 100,
    ) -> list[KnowledgeRecord]:
        """Read-only queue for human review. Oldest updated_at first."""
        ...

    def save_transition_with_audit(
        self,
        record: KnowledgeRecord,
        entry: AuditTrailEntry,
    ) -> KnowledgeRecord: ...

    def append_audit(self, entry: AuditTrailEntry) -> AuditTrailEntry: ...

    def list_audit_trail(self, knowledge_record_id: UUID) -> list[AuditTrailEntry]: ...

    def append_evidence_impact(self, impact: EvidenceImpactRecord) -> EvidenceImpactRecord: ...

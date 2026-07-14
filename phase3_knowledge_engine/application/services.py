"""Application services — orchestrates domain rules and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from phase3_knowledge_engine.application.state_transition_service import StateTransitionService
from phase3_knowledge_engine.config import MIN_OBSERVATIONS_FOR_PATTERN
from phase3_knowledge_engine.domain.confidence import compute_confidence
from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    EvidenceImpactRecord,
    EvidenceItem,
    KnowledgeRecord,
    MarketContext,
)
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.domain.rules import (
    DomainRuleViolation,
    assert_can_promote_to_knowledge,
    assert_hypothesis_explicit,
    assert_no_silent_knowledge_rewrite,
    assert_repeated_pattern_threshold,
    assert_single_observation_not_knowledge,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState


class KnowledgeEngineService:
    """Phase 3 use-cases. Not wired to Phase 2 runtime."""

    def __init__(self, repository: KnowledgeRepositoryPort):
        self.repo = repository
        self._transitions = StateTransitionService(repository)

    def register_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile:
        return self.repo.save_ea_profile(profile)

    def record_observation(
        self,
        ea_profile_id: UUID,
        evidence: EvidenceItem,
        *,
        similar_observation_count: int = 1,
    ) -> KnowledgeRecord:
        """Register raw evidence and open or extend a knowledge record at RawObservation."""
        evidence.ea_profile_id = ea_profile_id
        self.repo.save_evidence(evidence)

        record = KnowledgeRecord(
            id=uuid4(),
            ea_profile_id=ea_profile_id,
            validation_state=ValidationState.RAW_OBSERVATION.value,
            statement=f"Raw observation recorded for {evidence.symbol}",
            evidence_count=1,
            sample_size=1,
            supporting_evidence_ids=[evidence.id],
            confidence_score=0.0,
        )
        assert_single_observation_not_knowledge(1, ValidationState.RAW_OBSERVATION)
        self.repo.save_knowledge_record(record)
        self.repo.append_audit(AuditTrailEntry(
            id=uuid4(),
            knowledge_record_id=record.id,
            from_state="",
            to_state=ValidationState.RAW_OBSERVATION.value,
            transitioned_at=datetime.now(timezone.utc),
            actor="system",
            justification="Initial raw observation registered.",
            evidence_ids=[evidence.id],
        ))

        if similar_observation_count >= MIN_OBSERVATIONS_FOR_PATTERN:
            return self.promote_to_repeated_pattern(
                record.id,
                similar_observation_count=similar_observation_count,
                actor="system",
                justification="Configurable pattern threshold met; not validation.",
            )
        return record

    def promote_to_repeated_pattern(
        self,
        record_id: UUID,
        *,
        similar_observation_count: int,
        actor: str,
        justification: str,
    ) -> KnowledgeRecord:
        assert_repeated_pattern_threshold(similar_observation_count)
        record = self.repo.get_knowledge_record(record_id)
        if record:
            record.sample_size = similar_observation_count
            record.evidence_count = similar_observation_count
            self.repo.save_knowledge_record(record)
        return self._transitions.transition(
            record_id,
            ValidationState.REPEATED_PATTERN,
            actor=actor,
            justification=justification,
            human_review_recorded=False,
        )

    def create_hypothesis(
        self,
        record_id: UUID,
        *,
        statement: str,
        actor: str,
        justification: str,
    ) -> KnowledgeRecord:
        """Explicit human act — never auto-created from a single trade."""
        record = self.repo.get_knowledge_record(record_id)
        if not record:
            raise DomainRuleViolation("Record not found.")
        assert_hypothesis_explicit(
            explicit=True,
            from_state=ValidationState(record.validation_state),
        )
        assert_single_observation_not_knowledge(
            record.sample_size,
            ValidationState.HYPOTHESIS,
        )
        record.statement = statement
        self.repo.save_knowledge_record(record)
        return self._transitions.transition(
            record_id,
            ValidationState.HYPOTHESIS,
            actor=actor,
            justification=justification,
            human_review_recorded=True,
        )

    def submit_for_review(
        self,
        record_id: UUID,
        *,
        actor: str,
        justification: str,
        evidence_ids: list[UUID],
    ) -> KnowledgeRecord:
        record = self.repo.get_knowledge_record(record_id)
        if record:
            record.supporting_evidence_ids = evidence_ids
            record.evidence_count = len(evidence_ids)
            record.sample_size = len(evidence_ids)
            self.repo.save_knowledge_record(record)
        return self._transitions.transition(
            record_id,
            ValidationState.EVIDENCE_UNDER_REVIEW,
            actor=actor,
            justification=justification,
            evidence_ids=evidence_ids,
            human_review_recorded=True,
        )

    def apply_human_review_transition(
        self,
        record_id: UUID,
        to_state: ValidationState,
        *,
        actor: str,
        justification: str,
        evidence_ids: list[UUID] | None = None,
        relevance_for_decisions: str | None = None,
        context_documented: bool = False,
        material_contradictions_resolved: bool = False,
    ) -> KnowledgeRecord:
        record = self.repo.get_knowledge_record(record_id)
        if not record:
            raise DomainRuleViolation("Record not found.")

        if to_state is ValidationState.KNOWLEDGE:
            assert_can_promote_to_knowledge(
                relevance_for_decisions=relevance_for_decisions,
                evidence_count=record.evidence_count,
                sample_size=record.sample_size,
                context_documented=context_documented,
                human_review_recorded=True,
                reviewer=actor,
                material_contradictions_resolved=material_contradictions_resolved,
            )
            record.relevance_for_decisions = relevance_for_decisions
            record.context_documented = context_documented
            record.material_contradictions_resolved = material_contradictions_resolved
            self.repo.save_knowledge_record(record)

        # Advisory confidence — never authorizes promotion alone.
        record.confidence_score = compute_confidence(
            sample_size=record.sample_size,
            supporting_count=len(record.supporting_evidence_ids),
            contradictory_count=len(record.contradictory_evidence_ids),
            days_since_last_evidence=0,
            context_filled=4 if context_documented else 1,
            context_total=5,
        )
        self.repo.save_knowledge_record(record)

        return self._transitions.transition(
            record_id,
            to_state,
            actor=actor,
            justification=justification,
            evidence_ids=evidence_ids,
            human_review_recorded=True,
        )

    def register_evidence_impact_on_knowledge(
        self,
        knowledge_record_id: UUID,
        evidence_id: UUID,
        impact: str,
        *,
        actor: str,
        notes: str,
    ) -> EvidenceImpactRecord:
        """Rule 7: new evidence affects knowledge only via explicit impact."""
        assert_no_silent_knowledge_rewrite(impact)
        record = self.repo.get_knowledge_record(knowledge_record_id)
        if not record:
            raise DomainRuleViolation("Knowledge record not found.")
        if record.validation_state == ValidationState.KNOWLEDGE.value and impact in ("weaken", "review", "invalidate"):
            self._transitions.transition(
                knowledge_record_id,
                ValidationState.EVIDENCE_UNDER_REVIEW,
                actor=actor,
                justification=f"Knowledge reopened due to evidence impact: {impact}",
                evidence_ids=[evidence_id],
                human_review_recorded=True,
            )
        return self.repo.append_evidence_impact(EvidenceImpactRecord(
            id=uuid4(),
            knowledge_record_id=knowledge_record_id,
            evidence_id=evidence_id,
            impact=impact,  # type: ignore[arg-type]
            recorded_at=datetime.now(timezone.utc),
            actor=actor,
            notes=notes,
        ))

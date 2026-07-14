"""Centralized validation state machine — sole entry point for state changes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from phase3_knowledge_engine.domain.entities import AuditTrailEntry, KnowledgeRecord
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.domain.rules import DomainRuleViolation
from phase3_knowledge_engine.domain.validation_states import ValidationState, can_transition


class StateTransitionService:
    """All validation-state changes must pass through this service."""

    def __init__(self, repository: KnowledgeRepositoryPort) -> None:
        self._repo = repository

    def transition(
        self,
        record_id: UUID,
        to_state: ValidationState,
        *,
        actor: str,
        justification: str,
        evidence_ids: list[UUID] | None = None,
        human_review_recorded: bool = False,
    ) -> KnowledgeRecord:
        record = self._repo.get_knowledge_record(record_id)
        if not record:
            raise DomainRuleViolation(f"Knowledge record {record_id} not found.")
        from_state = ValidationState(record.validation_state)
        if not can_transition(from_state, to_state, human_review_recorded=human_review_recorded):
            raise DomainRuleViolation(
                f"Illegal transition {from_state.value} -> {to_state.value} "
                f"(human_review_recorded={human_review_recorded})."
            )
        record.validation_state = to_state.value
        if human_review_recorded:
            record.last_reviewed_at = datetime.now(timezone.utc)
            record.reviewed_by = actor
        self._repo.save_knowledge_record(record)
        self._repo.append_audit(
            AuditTrailEntry(
                id=uuid4(),
                knowledge_record_id=record_id,
                from_state=from_state.value,
                to_state=to_state.value,
                transitioned_at=datetime.now(timezone.utc),
                actor=actor,
                justification=justification,
                evidence_ids=evidence_ids or [],
            )
        )
        return record

"""Structural tests for centralized StateTransitionService."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from phase3_knowledge_engine.application.state_transition_service import StateTransitionService
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.rules import DomainRuleViolation
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


@pytest.fixture
def transition_service():
    with tempfile.TemporaryDirectory() as tmp:
        repo = KnowledgeRepository(Path(tmp) / "knowledge.db")
        yield StateTransitionService(repo), repo


def _seed_record(repo: KnowledgeRepository, state: ValidationState) -> KnowledgeRecord:
    profile_id = uuid4()
    repo.save_ea_profile(
        EAKnowledgeProfile(
            id=profile_id,
            ea_key="fsm-test",
            name="FSM Test",
            version="1.0.0",
            purpose="test",
            entry_rules="n/a",
            exit_rules="n/a",
            risk_rules={},
            permitted_symbols=["XAUUSD"],
            permitted_sessions=["London"],
            market_conditions={},
        )
    )
    record = KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile_id,
        validation_state=state.value,
        statement="test",
    )
    repo.save_knowledge_record(record)
    return record


class TestStateTransitionService:
    def test_all_transitions_go_through_service(self, transition_service):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.REPEATED_PATTERN)
        updated = service.transition(
            record.id,
            ValidationState.HYPOTHESIS,
            actor="analyst",
            justification="explicit",
            human_review_recorded=True,
        )
        assert updated.validation_state == ValidationState.HYPOTHESIS.value
        trail = repo.list_audit_trail(record.id)
        assert len(trail) == 1
        assert trail[0].to_state == ValidationState.HYPOTHESIS.value

    def test_repository_has_no_transition_state_method(self):
        assert not hasattr(KnowledgeRepository, "transition_state")

    def test_illegal_transition_rejected_by_service(self, transition_service):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.RAW_OBSERVATION)
        with pytest.raises(DomainRuleViolation, match="Illegal transition"):
            service.transition(
                record.id,
                ValidationState.KNOWLEDGE,
                actor="x",
                justification="bypass",
                human_review_recorded=True,
            )

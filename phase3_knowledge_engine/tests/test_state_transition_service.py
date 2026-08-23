"""Structural tests for centralized StateTransitionService."""

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from phase3_knowledge_engine.application.state_transition_service import StateTransitionService
from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    KnowledgeRecord,
)
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

    def test_transition_and_audit_commit_together(self, transition_service):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.REPEATED_PATTERN)

        service.transition(
            record.id,
            ValidationState.HYPOTHESIS,
            actor="analyst",
            justification="atomic commit",
            human_review_recorded=True,
        )

        persisted = repo.get_knowledge_record(record.id)
        trail = repo.list_audit_trail(record.id)
        assert persisted is not None
        assert persisted.validation_state == ValidationState.HYPOTHESIS.value
        assert len(trail) == 1
        assert trail[0].from_state == ValidationState.REPEATED_PATTERN.value
        assert trail[0].to_state == ValidationState.HYPOTHESIS.value

    def test_audit_failure_rolls_back_state_without_partial_transition(
        self,
        transition_service,
        monkeypatch,
    ):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.REPEATED_PATTERN)

        def fail_audit(entry, *, _connection=None):
            raise RuntimeError("simulated audit failure")

        monkeypatch.setattr(repo, "append_audit", fail_audit)

        with pytest.raises(RuntimeError, match="simulated audit failure"):
            service.transition(
                record.id,
                ValidationState.HYPOTHESIS,
                actor="analyst",
                justification="must roll back",
                human_review_recorded=True,
            )

        persisted = repo.get_knowledge_record(record.id)
        assert persisted is not None
        assert persisted.validation_state == ValidationState.REPEATED_PATTERN.value
        assert persisted.last_reviewed_at is None
        assert persisted.reviewed_by is None
        assert repo.list_audit_trail(record.id) == []

    def test_audit_history_cannot_be_overwritten(self, transition_service):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.REPEATED_PATTERN)
        service.transition(
            record.id,
            ValidationState.HYPOTHESIS,
            actor="original-actor",
            justification="original justification",
            human_review_recorded=True,
        )
        original = repo.list_audit_trail(record.id)[0]
        replacement = AuditTrailEntry(
            id=original.id,
            knowledge_record_id=record.id,
            from_state=original.from_state,
            to_state=ValidationState.INVALIDATED_CONCLUSION.value,
            transitioned_at=datetime.now(timezone.utc),
            actor="replacement-actor",
            justification="attempted overwrite",
        )

        with pytest.raises(sqlite3.IntegrityError):
            repo.append_audit(replacement)

        trail = repo.list_audit_trail(record.id)
        assert trail == [original]

    def test_transition_closes_every_sqlite_connection(
        self,
        transition_service,
        monkeypatch,
    ):
        service, repo = transition_service
        record = _seed_record(repo, ValidationState.REPEATED_PATTERN)
        opened_connections = []
        original_connect = repo._connect

        def tracked_connect():
            connection = original_connect()
            opened_connections.append(connection)
            return connection

        monkeypatch.setattr(repo, "_connect", tracked_connect)
        service.transition(
            record.id,
            ValidationState.HYPOTHESIS,
            actor="analyst",
            justification="connection closure",
            human_review_recorded=True,
        )

        assert len(opened_connections) == 2
        for connection in opened_connections:
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                connection.execute("SELECT 1")

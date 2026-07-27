"""Integration tests for the knowledge lifecycle (in-memory SQLite)."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, EvidenceItem, MarketContext
from phase3_knowledge_engine.domain.rules import DomainRuleViolation
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "knowledge.db"
        repo = KnowledgeRepository(db)
        yield KnowledgeEngineService(repo)


def _profile() -> EAKnowledgeProfile:
    return EAKnowledgeProfile(
        id=uuid4(),
        ea_key="london-scalper",
        name="London Scalper",
        version="2.1.0",
        purpose="Capture London open momentum on XAUUSD",
        entry_rules="Break of Asian range high with spread filter",
        exit_rules="Fixed RR 1:1.5 or session end",
        risk_rules={"max_daily_loss_pct": 2.0},
        permitted_symbols=["XAUUSD"],
        permitted_sessions=["London"],
        market_conditions={"preferred_regime": "trending"},
    )


def _evidence(ea_id, symbol="XAUUSD", session="London"):
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=ea_id,
        evidence_type="trade",
        occurred_at=datetime.now(timezone.utc),
        symbol=symbol,
        session=session,
        market_regime="trending",
        volatility=1.2,
        spread=18.0,
        pnl=42.5,
        ea_version="2.1.0",
        account_type="demo",
        test_type="forward",
        context=MarketContext(session=session, market_regime="trending", symbol=symbol),
    )


class TestKnowledgeLifecycle:
    def test_full_lifecycle_with_human_gates(self, engine):
        profile = engine.register_ea_profile(_profile())
        record = engine.record_observation(profile.id, _evidence(profile.id), similar_observation_count=1)
        assert record.validation_state == ValidationState.RAW_OBSERVATION.value

        record = engine.promote_to_repeated_pattern(
            record.id,
            similar_observation_count=2,
            actor="system",
            justification="Two similar London observations.",
        )
        assert record.validation_state == ValidationState.REPEATED_PATTERN.value

        record = engine.create_hypothesis(
            record.id,
            statement="EA performs better during London than New York",
            actor="analyst@forge",
            justification="Explicit hypothesis after repeated pattern.",
        )
        assert record.validation_state == ValidationState.HYPOTHESIS.value

        eids = [uuid4(), uuid4()]
        record = engine.submit_for_review(
            record.id,
            actor="analyst@forge",
            justification="Evidence package submitted.",
            evidence_ids=eids,
        )
        record.sample_size = 30
        record.evidence_count = 10
        engine.repo.save_knowledge_record(record)
        assert record.validation_state == ValidationState.EVIDENCE_UNDER_REVIEW.value

        for state in (
            ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
            ValidationState.FULLY_VALIDATED_CONCLUSION,
            ValidationState.KNOWLEDGE_CANDIDATE,
        ):
            record = engine.apply_human_review_transition(
                record.id,
                state,
                actor="lead@forge",
                justification=f"Human review approving {state.value}",
                context_documented=True,
            )
        assert record.validation_state == ValidationState.KNOWLEDGE_CANDIDATE.value

        record = engine.apply_human_review_transition(
            record.id,
            ValidationState.KNOWLEDGE,
            actor="lead@forge",
            justification="Promoted to knowledge after full validation.",
            relevance_for_decisions="Session allocation for XAUUSD EAs",
            context_documented=True,
            material_contradictions_resolved=True,
        )
        assert record.validation_state == ValidationState.KNOWLEDGE.value

    def test_single_observation_never_becomes_hypothesis(self, engine):
        profile = engine.register_ea_profile(_profile())
        record = engine.record_observation(profile.id, _evidence(profile.id), similar_observation_count=1)
        with pytest.raises(DomainRuleViolation):
            engine.create_hypothesis(
                record.id,
                statement="Auto guess from one trade",
                actor="bot",
                justification="Must fail: only one observation",
            )

    def test_invalidated_record_preserved_in_audit(self, engine):
        profile = engine.register_ea_profile(_profile())
        record = engine.record_observation(
            profile.id, _evidence(profile.id), similar_observation_count=2,
        )
        assert record.validation_state == ValidationState.REPEATED_PATTERN.value
        engine.create_hypothesis(
            record.id, statement="Test hypothesis",
            actor="a", justification="explicit",
        )
        record = engine.apply_human_review_transition(
            record.id,
            ValidationState.INVALIDATED_CONCLUSION,
            actor="reviewer",
            justification="Contradictory evidence on NY session.",
        )
        assert record.validation_state == ValidationState.INVALIDATED_CONCLUSION.value
        trail = engine.repo.list_audit_trail(record.id)
        assert any(e.to_state == ValidationState.INVALIDATED_CONCLUSION.value for e in trail)

    def test_evidence_impact_reopens_knowledge(self, engine):
        profile = engine.register_ea_profile(_profile())
        record = engine.record_observation(
            profile.id, _evidence(profile.id), similar_observation_count=2,
        )
        for step in (
            ValidationState.HYPOTHESIS,
            ValidationState.EVIDENCE_UNDER_REVIEW,
            ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
            ValidationState.FULLY_VALIDATED_CONCLUSION,
            ValidationState.KNOWLEDGE_CANDIDATE,
            ValidationState.KNOWLEDGE,
        ):
            if step is ValidationState.HYPOTHESIS:
                record = engine.create_hypothesis(
                    record.id, statement="s", actor="a", justification="j",
                )
            elif step is ValidationState.EVIDENCE_UNDER_REVIEW:
                record = engine.submit_for_review(
                    record.id, actor="a", justification="j", evidence_ids=[uuid4()],
                )
                record.sample_size = 30
                record.evidence_count = 10
                engine.repo.save_knowledge_record(record)
            elif step is ValidationState.KNOWLEDGE:
                record = engine.apply_human_review_transition(
                    record.id, step, actor="a", justification="j",
                    relevance_for_decisions="r", context_documented=True,
                    material_contradictions_resolved=True,
                )
            else:
                record = engine.apply_human_review_transition(
                    record.id, step, actor="a", justification="j",
                    context_documented=True,
                )

        new_ev = _evidence(profile.id, symbol="XAUUSD", session="New York")
        engine.repo.save_evidence(new_ev)
        engine.register_evidence_impact_on_knowledge(
            record.id, new_ev.id, "weaken",
            actor="analyst", notes="Recent NY losses contradict London edge.",
        )
        updated = engine.repo.get_knowledge_record(record.id)
        assert updated.validation_state == ValidationState.EVIDENCE_UNDER_REVIEW.value

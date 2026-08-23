"""Block 2 — context_signature grouping / pattern detection."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.config import MIN_OBSERVATIONS_FOR_PATTERN
from phase3_knowledge_engine.domain.entities import (
    EAKnowledgeProfile,
    EvidenceItem,
    MarketContext,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def _profile(repo: KnowledgeRepository, *, key: str = "ea-a") -> EAKnowledgeProfile:
    profile = EAKnowledgeProfile(
        id=uuid4(),
        ea_key=key,
        name="EA A",
        version="1.0.0",
        purpose="test",
        entry_rules="n/a",
        exit_rules="n/a",
        risk_rules={},
        permitted_symbols=["XAUUSD"],
        permitted_sessions=["London"],
        market_conditions={},
    )
    return repo.save_ea_profile(profile)


def _evidence(
    profile_id,
    *,
    symbol: str = "XAUUSD",
    session: str | None = "London",
    ea_version: str | None = "1.0.0",
    ticket: str = "1",
) -> EvidenceItem:
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=profile_id,
        evidence_type="trade",
        occurred_at=datetime.now(timezone.utc),
        symbol=symbol,
        session=session,
        ea_version=ea_version,
        context=MarketContext(session=session, symbol=symbol),
        source_system="mt5_bridge",
        external_id=ticket,
        pnl=1.0,
    )


def test_schema_version_is_at_least_three():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        assert repo._schema_version() >= 3


def test_first_evidence_creates_raw_observation_with_signature():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        engine = KnowledgeEngineService(repo)
        profile = _profile(repo)
        item = _evidence(profile.id, ticket="t1")
        record = engine.ingest_grouped_observation(item)
        assert record.validation_state == ValidationState.RAW_OBSERVATION.value
        assert record.evidence_count == 1
        assert record.supporting_evidence_ids == [item.id]
        expected = KnowledgeEngineService.compute_context_signature(
            profile.id, "1.0.0", "London", "XAUUSD"
        )
        assert record.context_signature == expected
        loaded = repo.get_knowledge_record(record.id)
        assert loaded is not None
        assert loaded.context_signature == expected


def test_second_matching_evidence_extends_same_record():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        engine = KnowledgeEngineService(repo)
        profile = _profile(repo)
        first = engine.ingest_grouped_observation(
            _evidence(profile.id, ticket="t1")
        )
        second_item = _evidence(profile.id, ticket="t2")
        second = engine.ingest_grouped_observation(second_item)
        assert second.id == first.id
        assert second.evidence_count == 2
        assert second_item.id in second.supporting_evidence_ids


def test_reaching_threshold_promotes_to_repeated_pattern():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        engine = KnowledgeEngineService(repo)
        profile = _profile(repo)
        assert MIN_OBSERVATIONS_FOR_PATTERN == 2
        first = engine.ingest_grouped_observation(
            _evidence(profile.id, ticket="t1")
        )
        assert first.validation_state == ValidationState.RAW_OBSERVATION.value
        second = engine.ingest_grouped_observation(
            _evidence(profile.id, ticket="t2")
        )
        assert second.id == first.id
        assert second.validation_state == ValidationState.REPEATED_PATTERN.value
        assert second.sample_size >= MIN_OBSERVATIONS_FOR_PATTERN


def test_post_hypothesis_match_uses_evidence_impact_not_mutation():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        engine = KnowledgeEngineService(repo)
        profile = _profile(repo)
        # Build a group to REPEATED_PATTERN then human-create HYPOTHESIS
        engine.ingest_grouped_observation(_evidence(profile.id, ticket="t1"))
        pattern = engine.ingest_grouped_observation(
            _evidence(profile.id, ticket="t2")
        )
        assert pattern.validation_state == ValidationState.REPEATED_PATTERN.value
        hypo = engine.create_hypothesis(
            pattern.id,
            statement="London XAUUSD edge holds",
            actor="founder",
            justification="Explicit hypothesis for impact routing test.",
        )
        assert hypo.validation_state == ValidationState.HYPOTHESIS.value
        before_ids = list(hypo.supporting_evidence_ids)
        before_count = hypo.evidence_count

        new_item = _evidence(profile.id, ticket="t3")
        returned = engine.ingest_grouped_observation(new_item)
        assert returned.id == hypo.id
        reloaded = repo.get_knowledge_record(hypo.id)
        assert reloaded is not None
        # Original hypothesis record not mutated by grouping
        assert reloaded.supporting_evidence_ids == before_ids
        assert reloaded.evidence_count == before_count
        assert reloaded.validation_state == ValidationState.HYPOTHESIS.value
        # Evidence was stored and impact recorded
        assert repo.get_evidence(new_item.id) is not None
        # find_knowledge_record_by_signature must NOT return the hypothesis record
        sig = hypo.context_signature
        assert sig is not None
        assert repo.find_knowledge_record_by_signature(sig) is None
        assert repo.find_post_hypothesis_record_by_signature(sig).id == hypo.id


def test_different_session_or_symbol_do_not_share_signature():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        engine = KnowledgeEngineService(repo)
        profile = _profile(repo)
        london = engine.ingest_grouped_observation(
            _evidence(profile.id, session="London", symbol="XAUUSD", ticket="a")
        )
        ny = engine.ingest_grouped_observation(
            _evidence(profile.id, session="NewYork", symbol="XAUUSD", ticket="b")
        )
        eurusd = engine.ingest_grouped_observation(
            _evidence(profile.id, session="London", symbol="EURUSD", ticket="c")
        )
        assert london.id != ny.id
        assert london.id != eurusd.id
        assert ny.id != eurusd.id
        assert london.context_signature != ny.context_signature
        assert london.context_signature != eurusd.context_signature

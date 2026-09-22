"""Gate 5 Stage 1 — Level A/B insights from KNOWLEDGE records only."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.config import PHASE3_KNOWLEDGE_ENGINE_ENABLED
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.insights import (
    CurrentContext,
    format_level_a,
    is_context_active_now,
    is_knowledge_stale,
    list_insights,
    main,
    parse_context_signature,
)


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def _profile(repo: KnowledgeRepository, *, key: str, version: str = "1.0.0") -> EAKnowledgeProfile:
    return repo.save_ea_profile(
        EAKnowledgeProfile(
            id=uuid4(),
            ea_key=key,
            name=key,
            version=version,
            purpose="test",
            entry_rules="n/a",
            exit_rules="n/a",
            risk_rules={},
            permitted_symbols=["XAUUSD"],
            permitted_sessions=["London"],
            market_conditions={},
            status="active",
        )
    )


def _record(
    profile: EAKnowledgeProfile,
    *,
    statement: str,
    state: ValidationState = ValidationState.KNOWLEDGE,
    session: str = "London",
    symbol: str = "XAUUSD",
    sample_size: int = 40,
    confidence: float = 0.82,
    reviewed_at: datetime | None = None,
) -> KnowledgeRecord:
    now = reviewed_at or datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    signature = KnowledgeEngineService.compute_context_signature(
        profile.id, profile.version, session, symbol
    )
    return KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile.id,
        validation_state=state.value,
        statement=statement,
        evidence_count=12,
        sample_size=sample_size,
        confidence_score=confidence,
        last_reviewed_at=now,
        reviewed_by="lead@forge",
        context_signature=signature,
        created_at=now,
        updated_at=now,
    )


def test_level_a_format_from_knowledge_record():
    profile_id = uuid4()
    reviewed = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    record = KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile_id,
        validation_state=ValidationState.KNOWLEDGE.value,
        statement="EA performs better during London than New York",
        sample_size=40,
        confidence_score=0.82,
        last_reviewed_at=reviewed,
    )
    text = format_level_a(record)
    assert text.startswith("EA performs better during London than New York ")
    assert "sample_size=40" in text
    assert "confidence_score=0.82" in text
    assert "last_reviewed_at=2026-07-15T12:00:00+00:00" in text
    assert "probably" not in text.lower()
    assert "suggest" not in text.lower()


def test_level_b_marks_active_only_when_context_matches():
    profile_id = uuid4()
    signature = KnowledgeEngineService.compute_context_signature(
        profile_id, "1.0.0", "London", "XAUUSD"
    )
    parsed = parse_context_signature(signature)
    assert parsed is not None
    assert parsed.session == "London"
    assert parsed.symbol == "XAUUSD"
    assert parsed.ea_version == "1.0.0"

    matching = CurrentContext(session="London", symbol="XAUUSD")
    assert is_context_active_now(signature, matching, ea_profile_id=profile_id) is True

    different_session = CurrentContext(session="NewYork", symbol="XAUUSD")
    assert is_context_active_now(signature, different_session, ea_profile_id=profile_id) is False

    different_symbol = CurrentContext(session="London", symbol="EURUSD")
    assert is_context_active_now(signature, different_symbol, ea_profile_id=profile_id) is False


def test_level_b_inactive_without_current_context_or_signature():
    profile_id = uuid4()
    signature = KnowledgeEngineService.compute_context_signature(
        profile_id, "1.0.0", "London", "XAUUSD"
    )
    assert is_context_active_now(signature, None) is False
    assert is_context_active_now(signature, CurrentContext()) is False
    assert is_context_active_now(None, CurrentContext(session="London", symbol="XAUUSD")) is False
    assert is_context_active_now(
        signature,
        CurrentContext(session="London", symbol="XAUUSD", ea_active=False),
    ) is False


def test_empty_list_when_no_validated_knowledge():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(
                profile,
                statement="Not yet validated",
                state=ValidationState.HYPOTHESIS,
            )
        )
        rows = list_insights(repository=repo, ea_profile_id=profile.id)
        assert rows == []


def test_list_insights_level_a_and_b_together():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper", version="1.0.0")
        knowledge = _record(
            profile,
            statement="Spread filter reduces London open losses",
            sample_size=55,
            confidence=0.91,
        )
        other_state = _record(
            profile,
            statement="Should not appear",
            state=ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
        )
        repo.save_knowledge_record(knowledge)
        repo.save_knowledge_record(other_state)

        current = CurrentContext(session="London", symbol="XAUUSD")
        rows = list_insights(
            repository=repo,
            ea_profile_id=profile.id,
            current_context=current,
        )
        assert len(rows) == 1
        insight = rows[0]
        assert insight.statement == "Spread filter reduces London open losses"
        assert insight.sample_size == 55
        assert insight.confidence_score == 0.91
        assert insight.is_context_active_now is True
        assert "sample_size=55" in insight.formatted
        assert "confidence_score=0.91" in insight.formatted

        mismatch = list_insights(
            repository=repo,
            ea_profile_id=profile.id,
            current_context=CurrentContext(session="NewYork", symbol="XAUUSD"),
        )
        assert len(mismatch) == 1
        assert mismatch[0].is_context_active_now is False


def test_cli_account_empty_and_match(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(profile, statement="Spread filter reduces London open losses")
        )

        code = main(["--db", db, "--account", "unknown-ea"])
        assert code == 0
        err = capsys.readouterr().err
        assert "No EA profile matching account=" in err

        code = main([
            "--db", db,
            "--account", "london-scalper",
            "--session", "London",
            "--symbol", "XAUUSD",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Spread filter reduces London open losses" in out
        assert "is_context_active_now=True" in out
        assert "is_stale=" in out
        assert "sample_size=" in out


NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def test_recent_knowledge_is_not_stale():
    reviewed = NOW - timedelta(days=89)
    assert is_knowledge_stale(reviewed, now=NOW) is False
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(profile, statement="Recent review", reviewed_at=reviewed)
        )
        rows = list_insights(repository=repo, ea_profile_id=profile.id, now=NOW)
        assert len(rows) == 1
        assert rows[0].is_stale is False


def test_knowledge_older_than_90_days_is_stale():
    reviewed = NOW - timedelta(days=91)
    assert is_knowledge_stale(reviewed, now=NOW) is True
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(profile, statement="Old review", reviewed_at=reviewed)
        )
        rows = list_insights(repository=repo, ea_profile_id=profile.id, now=NOW)
        assert len(rows) == 1
        assert rows[0].is_stale is True


def test_knowledge_exactly_90_days_is_stale():
    reviewed = NOW - timedelta(days=90)
    assert is_knowledge_stale(reviewed, now=NOW) is True
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(profile, statement="Boundary review", reviewed_at=reviewed)
        )
        rows = list_insights(repository=repo, ea_profile_id=profile.id, now=NOW)
        assert len(rows) == 1
        assert rows[0].is_stale is True


def test_phase3_flag_remains_off_by_default():
    assert PHASE3_KNOWLEDGE_ENGINE_ENABLED is False
    env = os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower()
    assert env not in ("1", "true", "yes")

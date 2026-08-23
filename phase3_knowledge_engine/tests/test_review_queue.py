"""Block 3 — list knowledge records by validation state (human review queue)."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.review import format_record_line, list_for_review, main


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def _profile(repo: KnowledgeRepository, *, key: str) -> EAKnowledgeProfile:
    return repo.save_ea_profile(
        EAKnowledgeProfile(
            id=uuid4(),
            ea_key=key,
            name=key,
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


def _record(
    profile_id,
    *,
    state: ValidationState,
    statement: str,
    updated_at: datetime,
) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile_id,
        validation_state=state.value,
        statement=statement,
        evidence_count=2,
        sample_size=2,
        context_signature=f"{profile_id}-1.0.0-London-XAUUSD",
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_list_returns_only_requested_state():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        p = _profile(repo, key="ea-a")
        now = datetime.now(timezone.utc)
        raw = _record(p.id, state=ValidationState.RAW_OBSERVATION, statement="raw", updated_at=now)
        pattern = _record(
            p.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="pattern",
            updated_at=now + timedelta(seconds=1),
        )
        repo.save_knowledge_record(raw)
        repo.save_knowledge_record(pattern)
        listed = repo.list_knowledge_records_by_state(ValidationState.REPEATED_PATTERN)
        assert len(listed) == 1
        assert listed[0].id == pattern.id
        assert listed[0].validation_state == ValidationState.REPEATED_PATTERN.value


def test_ea_profile_id_filter_narrows():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        a = _profile(repo, key="ea-a")
        b = _profile(repo, key="ea-b")
        now = datetime.now(timezone.utc)
        ra = _record(a.id, state=ValidationState.REPEATED_PATTERN, statement="a", updated_at=now)
        rb = _record(
            b.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="b",
            updated_at=now + timedelta(seconds=1),
        )
        repo.save_knowledge_record(ra)
        repo.save_knowledge_record(rb)
        only_a = repo.list_knowledge_records_by_state(
            ValidationState.REPEATED_PATTERN, ea_profile_id=a.id
        )
        assert [r.id for r in only_a] == [ra.id]


def test_ordering_is_oldest_updated_first():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        p = _profile(repo, key="ea-a")
        base = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
        older = _record(
            p.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="older",
            updated_at=base,
        )
        newer = _record(
            p.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="newer",
            updated_at=base + timedelta(hours=2),
        )
        # Insert newer first to prove ORDER BY, not insert order
        repo.save_knowledge_record(newer)
        repo.save_knowledge_record(older)
        # save_knowledge_record stamps updated_at=now; pin timestamps for the assert
        with repo._connection() as cx:
            cx.execute(
                "UPDATE knowledge_records SET updated_at = ? WHERE id = ?",
                ((base + timedelta(hours=2)).isoformat(), str(newer.id)),
            )
            cx.execute(
                "UPDATE knowledge_records SET updated_at = ? WHERE id = ?",
                (base.isoformat(), str(older.id)),
            )
        listed = repo.list_knowledge_records_by_state(ValidationState.REPEATED_PATTERN)
        assert [r.statement for r in listed] == ["older", "newer"]


def test_empty_result_when_nothing_matches_is_not_error():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        listed = repo.list_knowledge_records_by_state(ValidationState.HYPOTHESIS)
        assert listed == []
        # CLI helper also returns empty list (exit handled by main)
        rows = list_for_review(
            db_path=str(Path(tmp) / "knowledge.db"),
            state=ValidationState.REPEATED_PATTERN,
            ea_key=None,
            limit=50,
        )
        assert rows == []
        assert main(["--state", "repeated_pattern", "--db", str(Path(tmp) / "knowledge.db")]) == 0


def test_cli_ea_key_filter_and_format_line():
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        a = _profile(repo, key="london-scalper")
        b = _profile(repo, key="other")
        now = datetime.now(timezone.utc)
        ra = _record(
            a.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="London edge",
            updated_at=now,
        )
        rb = _record(
            b.id,
            state=ValidationState.REPEATED_PATTERN,
            statement="Other",
            updated_at=now + timedelta(seconds=1),
        )
        repo.save_knowledge_record(ra)
        repo.save_knowledge_record(rb)
        rows = list_for_review(
            db_path=db,
            state=ValidationState.REPEATED_PATTERN,
            ea_key="london-scalper",
            limit=100,
        )
        assert len(rows) == 1
        assert rows[0].id == ra.id
        line = format_record_line(rows[0])
        assert str(ra.id) in line
        assert "London edge" in line
        assert "context_signature=" in line

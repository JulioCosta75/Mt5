"""Block 6 — technical report of supported (KNOWLEDGE) conclusions."""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.report import build_technical_report, main


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def _profile(
    repo: KnowledgeRepository,
    *,
    key: str,
    name: str | None = None,
    version: str = "2.1.0",
) -> EAKnowledgeProfile:
    return repo.save_ea_profile(
        EAKnowledgeProfile(
            id=uuid4(),
            ea_key=key,
            name=name or key,
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


def _knowledge_record(
    profile_id,
    *,
    statement: str,
    state: ValidationState = ValidationState.KNOWLEDGE,
    updated_at: datetime | None = None,
) -> KnowledgeRecord:
    now = updated_at or datetime.now(timezone.utc)
    return KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile_id,
        validation_state=state.value,
        statement=statement,
        evidence_count=12,
        sample_size=40,
        date_range_start=date(2026, 1, 1),
        date_range_end=date(2026, 6, 30),
        confidence_score=0.82,
        last_reviewed_at=now,
        reviewed_by="lead@forge",
        created_at=now,
        updated_at=now,
    )


def test_report_includes_only_knowledge_state_records():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        p = _profile(repo, key="london-scalper", name="London Scalper")
        now = datetime.now(timezone.utc)
        knowledge = _knowledge_record(
            p.id,
            statement="EA performs better during London than New York",
            updated_at=now,
        )
        earlier = _knowledge_record(
            p.id,
            statement="Should not appear — still hypothesis",
            state=ValidationState.HYPOTHESIS,
            updated_at=now + timedelta(seconds=1),
        )
        provisional = _knowledge_record(
            p.id,
            statement="Should not appear — provisional only",
            state=ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
            updated_at=now + timedelta(seconds=2),
        )
        repo.save_knowledge_record(knowledge)
        repo.save_knowledge_record(earlier)
        repo.save_knowledge_record(provisional)

        report = build_technical_report(repository=repo)
        assert "EA performs better during London than New York" in report
        assert "Should not appear — still hypothesis" not in report
        assert "Should not appear — provisional only" not in report
        assert "1 supported conclusion" in report


def test_ea_profile_id_filter_narrows():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        a = _profile(repo, key="ea-a", name="Alpha")
        b = _profile(repo, key="ea-b", name="Beta")
        now = datetime.now(timezone.utc)
        ra = _knowledge_record(a.id, statement="Conclusion for Alpha only", updated_at=now)
        rb = _knowledge_record(
            b.id,
            statement="Conclusion for Beta only",
            updated_at=now + timedelta(seconds=1),
        )
        repo.save_knowledge_record(ra)
        repo.save_knowledge_record(rb)

        report = build_technical_report(a.id, repository=repo)
        assert "Conclusion for Alpha only" in report
        assert "Conclusion for Beta only" not in report
        assert "ea_key=ea-a" in report


def test_empty_report_is_not_an_error():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        report = build_technical_report(repository=repo)
        assert "No supported conclusions" in report
        assert "knowledge" in report.lower()


def test_report_contains_required_fields():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        p = _profile(
            repo,
            key="london-scalper",
            name="London Scalper",
            version="2.1.0",
        )
        reviewed_at = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        record = _knowledge_record(
            p.id,
            statement="Spread filter reduces London open losses",
            updated_at=reviewed_at,
        )
        record.confidence_score = 0.91
        record.evidence_count = 15
        record.sample_size = 55
        record.date_range_start = date(2026, 2, 1)
        record.date_range_end = date(2026, 7, 1)
        record.reviewed_by = "lead@forge"
        record.last_reviewed_at = reviewed_at
        repo.save_knowledge_record(record)

        report = build_technical_report(repository=repo)
        assert "Spread filter reduces London open losses" in report
        assert "ea_key=london-scalper" in report
        assert "name=London Scalper" in report
        assert "version=2.1.0" in report
        assert "confidence_score: 0.91" in report
        assert "evidence_count: 15" in report
        assert "sample_size: 55" in report
        assert "date_range_start: 2026-02-01" in report
        assert "date_range_end: 2026-07-01" in report
        assert "last_reviewed_at: 2026-07-15T12:00:00+00:00" in report
        assert "reviewed_by: lead@forge" in report


def test_cli_report_ea_filter(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        a = _profile(repo, key="ea-a", name="Alpha")
        b = _profile(repo, key="ea-b", name="Beta")
        now = datetime.now(timezone.utc)
        repo.save_knowledge_record(
            _knowledge_record(a.id, statement="Only Alpha", updated_at=now)
        )
        repo.save_knowledge_record(
            _knowledge_record(
                b.id,
                statement="Only Beta",
                updated_at=now + timedelta(seconds=1),
            )
        )
        code = main(["--db", db, "--ea", "ea-a"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Only Alpha" in out
        assert "Only Beta" not in out

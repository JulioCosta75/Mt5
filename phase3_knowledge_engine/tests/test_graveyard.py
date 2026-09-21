"""Gate 5 — isolated graveyard of INVALIDATED_CONCLUSION records."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.config import PHASE3_KNOWLEDGE_ENGINE_ENABLED
from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    KnowledgeRecord,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.graveyard import list_graveyard, main
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


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
            status="active",
        )
    )


def _record(
    profile: EAKnowledgeProfile,
    *,
    statement: str,
    state: ValidationState,
) -> KnowledgeRecord:
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    return KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile.id,
        validation_state=state.value,
        statement=statement,
        evidence_count=4,
        sample_size=12,
        last_reviewed_at=now,
        reviewed_by="lead@forge",
        created_at=now,
        updated_at=now,
    )


def _append_invalidation(
    repo: KnowledgeRepository,
    record: KnowledgeRecord,
    *,
    actor: str,
    justification: str,
    at: datetime,
    from_state: ValidationState = ValidationState.HYPOTHESIS,
) -> None:
    repo.append_audit(
        AuditTrailEntry(
            id=uuid4(),
            knowledge_record_id=record.id,
            from_state=from_state.value,
            to_state=ValidationState.INVALIDATED_CONCLUSION.value,
            transitioned_at=at,
            actor=actor,
            justification=justification,
        )
    )


def test_only_invalidated_conclusion_appears():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        invalidated = _record(
            profile,
            statement="London open always profitable",
            state=ValidationState.INVALIDATED_CONCLUSION,
        )
        knowledge = _record(
            profile,
            statement="Should not appear",
            state=ValidationState.KNOWLEDGE,
        )
        hypothesis = _record(
            profile,
            statement="Also should not appear",
            state=ValidationState.HYPOTHESIS,
        )
        repo.save_knowledge_record(invalidated)
        repo.save_knowledge_record(knowledge)
        repo.save_knowledge_record(hypothesis)
        _append_invalidation(
            repo,
            invalidated,
            actor="reviewer@forge",
            justification="Contradictory evidence on NY session.",
            at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
        )

        rows = list_graveyard(repository=repo, ea_profile_id=profile.id)
        assert len(rows) == 1
        entry = rows[0]
        assert entry.knowledge_record_id == invalidated.id
        assert entry.statement == "London open always profitable"
        assert entry.decided_by == "reviewer@forge"
        assert entry.justification == "Contradictory evidence on NY session."
        assert entry.invalidated_at == datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)


def test_empty_list_when_no_invalidated():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        repo.save_knowledge_record(
            _record(
                profile,
                statement="Validated knowledge stays out of the graveyard",
                state=ValidationState.KNOWLEDGE,
            )
        )
        rows = list_graveyard(repository=repo, ea_profile_id=profile.id)
        assert rows == []


def test_justification_included_when_audit_exists():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        with_audit = _record(
            profile,
            statement="Spread filter is unnecessary",
            state=ValidationState.INVALIDATED_CONCLUSION,
        )
        without_audit = _record(
            profile,
            statement="Always trade Friday close",
            state=ValidationState.INVALIDATED_CONCLUSION,
        )
        repo.save_knowledge_record(with_audit)
        repo.save_knowledge_record(without_audit)
        _append_invalidation(
            repo,
            with_audit,
            actor="lead@forge",
            justification="Sample was selection-biased.",
            at=datetime(2026, 8, 1, 14, 30, tzinfo=timezone.utc),
        )

        rows = list_graveyard(repository=repo, ea_profile_id=profile.id)
        by_id = {row.knowledge_record_id: row for row in rows}
        assert set(by_id) == {with_audit.id, without_audit.id}

        present = by_id[with_audit.id]
        assert present.justification == "Sample was selection-biased."
        assert present.decided_by == "lead@forge"
        assert "Sample was selection-biased." in present.formatted
        assert "decided_by=lead@forge" in present.formatted

        missing = by_id[without_audit.id]
        assert missing.justification is None
        assert missing.decided_by is None
        assert missing.invalidated_at is None
        assert "justification=''" in missing.formatted
        assert "invent" not in missing.formatted.lower()


def test_cli_account_empty_and_match(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        profile = _profile(repo, key="london-scalper")
        record = _record(
            profile,
            statement="London open always profitable",
            state=ValidationState.INVALIDATED_CONCLUSION,
        )
        repo.save_knowledge_record(record)
        _append_invalidation(
            repo,
            record,
            actor="reviewer@forge",
            justification="Contradictory evidence on NY session.",
            at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
        )

        code = main(["--db", db, "--account", "unknown-ea"])
        assert code == 0
        err = capsys.readouterr().err
        assert "No EA profile matching account=" in err

        code = main(["--db", db, "--account", "london-scalper"])
        assert code == 0
        out = capsys.readouterr().out
        assert "London open always profitable" in out
        assert "reviewer@forge" in out
        assert "Contradictory evidence on NY session." in out
        assert "1 invalidated conclusion" in out

        other = _profile(repo, key="ny-scalper")
        code = main(["--db", db, "--account", "ny-scalper"])
        assert code == 0
        empty = capsys.readouterr().out
        assert "No invalidated conclusions." in empty
        assert other.ea_key == "ny-scalper"


def test_phase2_server_has_no_phase3_reference():
    repo_root = Path(__file__).resolve().parents[2]
    server = repo_root / "backend" / "server.py"
    text = server.read_text(encoding="utf-8")
    assert "phase3_knowledge_engine" not in text
    assert "PHASE3_KNOWLEDGE_ENGINE_ENABLED" not in text
    assert PHASE3_KNOWLEDGE_ENGINE_ENABLED is False
    env = os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower()
    assert env not in ("1", "true", "yes")

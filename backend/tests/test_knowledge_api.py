"""Gate 5 Stage 2 — flag-gated /api/knowledge/v1 read-only mounts."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    KnowledgeRecord,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
for path in (str(BACKEND), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ["ATLAS_STORE"] = "sqlite"
os.environ.pop("MT5_BRIDGE_URL", None)
os.environ.pop("MT5_BRIDGE_URLS", None)


ROUTES = (
    "/api/knowledge/v1/status",
    "/api/knowledge/v1/insights?account_id=london-scalper",
    "/api/knowledge/v1/graveyard?account_id=london-scalper",
    "/api/knowledge/v1/correlation?account_id=demo-1&ea_a=london-scalper&ea_b=ny-scalper",
)


def _client(monkeypatch, *, enabled: bool, db_path: str | None = None):
    from fastapi.testclient import TestClient
    import server as server_mod

    monkeypatch.setenv("ATLAS_STORE", "sqlite")
    monkeypatch.delenv("MT5_BRIDGE_URL", raising=False)
    monkeypatch.delenv("MT5_BRIDGE_URLS", raising=False)

    if enabled:
        monkeypatch.setenv("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "true")
    else:
        monkeypatch.setenv("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false")
    if db_path:
        monkeypatch.setenv("PHASE3_KNOWLEDGE_DB_PATH", db_path)
    return TestClient(server_mod.app)


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


def _knowledge_record(profile: EAKnowledgeProfile, *, statement: str) -> KnowledgeRecord:
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    signature = KnowledgeEngineService.compute_context_signature(
        profile.id, profile.version, "London", "XAUUSD"
    )
    return KnowledgeRecord(
        id=uuid4(),
        ea_profile_id=profile.id,
        validation_state=ValidationState.KNOWLEDGE.value,
        statement=statement,
        evidence_count=12,
        sample_size=40,
        confidence_score=0.82,
        last_reviewed_at=now,
        reviewed_by="lead@forge",
        context_signature=signature,
        created_at=now,
        updated_at=now,
    )


def test_flag_off_returns_404_on_all_four_routes(monkeypatch):
    client = _client(monkeypatch, enabled=False)
    for path in ROUTES:
        r = client.get(path)
        assert r.status_code == 404, path
        body = r.json()
        assert "insights" not in body
        assert "enabled" not in body


def test_flag_on_status_and_empty_account(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        KnowledgeRepository(db)
        client = _client(monkeypatch, enabled=True, db_path=db)
        status = client.get("/api/knowledge/v1/status")
        assert status.status_code == 200
        assert status.json() == {"enabled": True}

        empty = client.get("/api/knowledge/v1/insights", params={"account_id": "unknown-ea"})
        assert empty.status_code == 200
        body = empty.json()
        assert body["insights"] == []
        assert body["counts"]["validated"] == 0
        assert body["ea_key"] is None

        grave = client.get("/api/knowledge/v1/graveyard", params={"account_id": "unknown-ea"})
        assert grave.status_code == 200
        assert grave.json()["entries"] == []
        assert grave.json()["count"] == 0


def test_flag_on_insights_and_graveyard_scoped_to_account(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        london = _profile(repo, key="london-scalper")
        ny = _profile(repo, key="ny-scalper")
        repo.save_knowledge_record(
            _knowledge_record(london, statement="Spread filter reduces London open losses")
        )
        repo.save_knowledge_record(
            _knowledge_record(ny, statement="Should not leak to london account")
        )
        invalidated = KnowledgeRecord(
            id=uuid4(),
            ea_profile_id=london.id,
            validation_state=ValidationState.INVALIDATED_CONCLUSION.value,
            statement="London open always profitable",
            created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        )
        repo.save_knowledge_record(invalidated)
        repo.append_audit(
            AuditTrailEntry(
                id=uuid4(),
                knowledge_record_id=invalidated.id,
                from_state=ValidationState.HYPOTHESIS.value,
                to_state=ValidationState.INVALIDATED_CONCLUSION.value,
                transitioned_at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
                actor="reviewer@forge",
                justification="Contradictory evidence on NY session.",
            )
        )

        client = _client(monkeypatch, enabled=True, db_path=db)
        r = client.get(
            "/api/knowledge/v1/insights",
            params={"account_id": "london-scalper", "session": "London", "symbol": "XAUUSD"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ea_key"] == "london-scalper"
        assert len(body["insights"]) == 1
        assert body["insights"][0]["statement"] == "Spread filter reduces London open losses"
        assert "is_stale" in body["insights"][0]
        assert body["insights"][0]["is_context_active_now"] is True
        assert "Should not leak" not in r.text

        g = client.get("/api/knowledge/v1/graveyard", params={"account_id": "london-scalper"})
        assert g.status_code == 200
        entries = g.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["statement"] == "London open always profitable"
        assert entries[0]["justification"] == "Contradictory evidence on NY session."
        assert entries[0]["decided_by"] == "reviewer@forge"


def test_flag_on_correlation_insufficient_omits_number(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        _profile(repo, key="london-scalper")
        client = _client(monkeypatch, enabled=True, db_path=db)
        r = client.get(
            "/api/knowledge/v1/correlation",
            params={
                "account_id": "demo-1",
                "ea_a": "london-scalper",
                "ea_b": "missing-ea",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["insufficient"] is True
        assert body["coincidence"] is None
        assert "dados insuficientes" in body["reason"]


def test_no_write_routes_on_knowledge_surface():
    source = (BACKEND / "knowledge_routes.py").read_text(encoding="utf-8")
    server = (BACKEND / "server.py").read_text(encoding="utf-8")
    assert "@router.post" not in source
    assert "@router.put" not in source
    assert "@router.delete" not in source
    assert "@app.post(\"/api/knowledge" not in server
    assert "include_router(knowledge_router)" in server

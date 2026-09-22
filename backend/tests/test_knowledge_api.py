"""Gate 5 Stage 2b — flag-gated /api/knowledge/v1 read-only mounts."""

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
    EvidenceItem,
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
    "/api/knowledge/v1/ea-profiles?account_id=london-scalper",
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


def _evidence(
    profile: EAKnowledgeProfile,
    *,
    account_id: str | None,
    ticket: str,
) -> EvidenceItem:
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=profile.id,
        evidence_type="trade",
        occurred_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
        symbol="XAUUSD",
        session="London",
        pnl=-1.5,
        account_type="demo",
        account_id=account_id,
        test_type="forward",
        source_system="mt5_bridge",
        external_id=ticket,
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


def test_flag_off_returns_404_on_all_mounted_routes(monkeypatch):
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

        profiles = client.get("/api/knowledge/v1/ea-profiles", params={"account_id": "unknown-ea"})
        assert profiles.status_code == 200
        body = profiles.json()
        assert body["profiles"] == []
        assert body["ea_key"] is None
        assert body["counts"] == {
            "under_review": 0,
            "candidates": 0,
            "validated": 0,
            "graveyard": 0,
        }


def test_flag_on_insights_and_graveyard_scoped_to_account(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        london = _profile(repo, key="london-scalper")
        ny = _profile(repo, key="ny-scalper")
        repo.save_evidence(_evidence(london, account_id="acc-london", ticket="L-1"))
        repo.save_evidence(_evidence(ny, account_id="acc-ny", ticket="N-1"))
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
            params={"account_id": "acc-london", "session": "London", "symbol": "XAUUSD"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ea_key"] == "london-scalper"
        assert len(body["insights"]) == 1
        assert body["insights"][0]["statement"] == "Spread filter reduces London open losses"
        assert "is_stale" in body["insights"][0]
        assert body["insights"][0]["is_context_active_now"] is True
        assert "Should not leak" not in r.text

        g = client.get("/api/knowledge/v1/graveyard", params={"account_id": "acc-london"})
        assert g.status_code == 200
        entries = g.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["statement"] == "London open always profitable"
        assert entries[0]["justification"] == "Contradictory evidence on NY session."
        assert entries[0]["decided_by"] == "reviewer@forge"

        by_ea_key = client.get(
            "/api/knowledge/v1/insights", params={"account_id": "london-scalper"}
        )
        assert by_ea_key.status_code == 200
        assert by_ea_key.json()["insights"] == []


def test_flag_on_ea_profiles_fields_and_unknown_account(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        london = _profile(repo, key="london-scalper")
        _profile(repo, key="ny-scalper")
        repo.save_evidence(_evidence(london, account_id="acc-london", ticket="L-1"))
        repo.save_knowledge_record(
            _knowledge_record(london, statement="Spread filter reduces London open losses")
        )

        client = _client(monkeypatch, enabled=True, db_path=db)
        unknown = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "unknown-ea"}
        )
        assert unknown.status_code == 200
        assert unknown.json()["profiles"] == []

        no_evidence = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "london-scalper"}
        )
        assert no_evidence.status_code == 200
        assert no_evidence.json()["profiles"] == []

        r = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "acc-london"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ea_key"] == "london-scalper"
        keys = {row["ea_key"]: row for row in body["profiles"]}
        assert set(keys) == {"london-scalper"}
        row = keys["london-scalper"]
        assert row["name"] == "london-scalper"
        assert row["version"] == "1.0.0"
        assert row["purpose"] == "test"
        assert row["entry_rules"] == "n/a"
        assert row["exit_rules"] == "n/a"
        assert row["risk_rules"] == {}
        assert row["permitted_symbols"] == ["XAUUSD"]
        assert row["permitted_sessions"] == ["London"]
        assert row["status"] == "active"
        assert body["counts"]["validated"] == 1
        statements = [rec["statement"] for rec in row["records"]]
        assert "Spread filter reduces London open losses" in statements
        assert all(
            rec["validation_state"] == ValidationState.KNOWLEDGE.value
            for rec in row["records"]
        )


def test_two_accounts_do_not_mix_on_ea_profiles_insights_graveyard(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        london = _profile(repo, key="london-scalper")
        ny = _profile(repo, key="ny-scalper")
        repo.save_evidence(_evidence(london, account_id="acc-a", ticket="A-1"))
        repo.save_evidence(_evidence(ny, account_id="acc-b", ticket="B-1"))
        repo.save_knowledge_record(
            _knowledge_record(london, statement="London fact stays on acc-a")
        )
        repo.save_knowledge_record(
            _knowledge_record(ny, statement="NY fact stays on acc-b")
        )
        ny_dead = KnowledgeRecord(
            id=uuid4(),
            ea_profile_id=ny.id,
            validation_state=ValidationState.INVALIDATED_CONCLUSION.value,
            statement="NY invalidated stays on acc-b",
            created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        )
        repo.save_knowledge_record(ny_dead)
        repo.append_audit(
            AuditTrailEntry(
                id=uuid4(),
                knowledge_record_id=ny_dead.id,
                from_state=ValidationState.HYPOTHESIS.value,
                to_state=ValidationState.INVALIDATED_CONCLUSION.value,
                transitioned_at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
                actor="reviewer@forge",
                justification="Only on account B.",
            )
        )

        client = _client(monkeypatch, enabled=True, db_path=db)
        a_profiles = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "acc-a"}
        ).json()
        assert [p["ea_key"] for p in a_profiles["profiles"]] == ["london-scalper"]
        a_text = str(a_profiles)
        assert "London fact stays on acc-a" in a_text
        assert "NY fact stays on acc-b" not in a_text
        assert "NY invalidated" not in a_text

        b_profiles = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "acc-b"}
        ).json()
        assert [p["ea_key"] for p in b_profiles["profiles"]] == ["ny-scalper"]
        b_text = str(b_profiles)
        assert "NY fact stays on acc-b" in b_text
        assert "London fact stays on acc-a" not in b_text

        a_ins = client.get(
            "/api/knowledge/v1/insights", params={"account_id": "acc-a"}
        ).json()
        assert [row["statement"] for row in a_ins["insights"]] == [
            "London fact stays on acc-a"
        ]
        b_ins = client.get(
            "/api/knowledge/v1/insights", params={"account_id": "acc-b"}
        ).json()
        assert [row["statement"] for row in b_ins["insights"]] == [
            "NY fact stays on acc-b"
        ]

        a_grave = client.get(
            "/api/knowledge/v1/graveyard", params={"account_id": "acc-a"}
        ).json()
        assert a_grave["entries"] == []
        b_grave = client.get(
            "/api/knowledge/v1/graveyard", params={"account_id": "acc-b"}
        ).json()
        assert [row["statement"] for row in b_grave["entries"]] == [
            "NY invalidated stays on acc-b"
        ]

        zero = client.get(
            "/api/knowledge/v1/ea-profiles", params={"account_id": "acc-empty"}
        ).json()
        assert zero["profiles"] == []
        assert zero["counts"]["validated"] == 0


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

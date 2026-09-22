"""Evidence-derived MT5 account scoping (Gate 5 — no invented EA↔account map)."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.adapters.ingestion.mt5_bridge_evidence_source import (
    resolve_account_id,
)
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, EvidenceItem
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.ingest import run_file_ingest


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


def _trade(profile: EAKnowledgeProfile, *, account_id: str | None, ticket: str) -> EvidenceItem:
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=profile.id,
        evidence_type="trade",
        occurred_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
        symbol="XAUUSD",
        pnl=-2.0,
        account_type="demo",
        account_id=account_id,
        test_type="forward",
        source_system="mt5_bridge",
        external_id=ticket,
    )


def test_schema_version_is_at_least_four():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        assert repo._schema_version() >= 4


def test_resolve_account_id_from_bridge_payload():
    assert resolve_account_id(None) is None
    assert resolve_account_id({}) is None
    assert resolve_account_id({"server": "Demo"}) is None
    assert resolve_account_id({"login": 5609382}) == "5609382"
    assert resolve_account_id({"id": "MT5-5609382", "login": 5609382}) == "MT5-5609382"
    assert resolve_account_id({"account_id": "acc-a", "login": 1}) == "acc-a"
    assert resolve_account_id({"login": ""}) is None


def test_list_ea_profile_ids_isolates_each_account_among_many():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        seeds = (
            ("ea-a", "acc-1"),
            ("ea-b", "acc-2"),
            ("ea-c", "acc-3"),
            ("ea-d", "acc-4"),
        )
        by_account: dict[str, EAKnowledgeProfile] = {}
        for i, (key, account_id) in enumerate(seeds):
            profile = _profile(repo, key=key)
            by_account[account_id] = profile
            repo.save_evidence(_trade(profile, account_id=account_id, ticket=f"T-{i}"))
        orphan = _profile(repo, key="ea-orphan")
        repo.save_evidence(_trade(orphan, account_id=None, ticket="O-1"))

        all_ids = {p.id for p in by_account.values()} | {orphan.id}
        for account_id, profile in by_account.items():
            found = repo.list_ea_profile_ids_with_evidence_for_account(account_id)
            assert found == [profile.id], account_id
            assert (all_ids - {profile.id}).isdisjoint(found)

        assert repo.list_ea_profile_ids_with_evidence_for_account("acc-empty") == []
        assert repo.list_ea_profile_ids_with_evidence_for_account("  ") == []
        assert repo.list_ea_profile_ids_with_evidence_for_account("ea-a") == []


def test_lookup_recognizes_phase2_mt5_login_alias():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="ea-live")
        repo.save_evidence(_trade(profile, account_id="5609382", ticket="L-1"))
        assert repo.list_ea_profile_ids_with_evidence_for_account("MT5-5609382") == [
            profile.id
        ]
        assert repo.list_ea_profile_ids_with_evidence_for_account("5609382") == [
            profile.id
        ]


def test_file_ingest_account_id_omitted_stays_none():
    with tempfile.TemporaryDirectory() as tmp:
        deals = Path(tmp) / "deals.json"
        deals.write_text(
            json.dumps(
                [
                    {
                        "ticket": 1,
                        "magic": 11,
                        "symbol": "XAUUSD",
                        "profit": 1.0,
                        "swap": 0,
                        "commission": 0,
                        "time": "2026-08-01T10:00:00+00:00",
                    }
                ]
            ),
            encoding="utf-8",
        )
        db = str(Path(tmp) / "knowledge.db")
        run_file_ingest(
            file_path=deals,
            db_path=db,
            limit=10,
            account_type="demo",
            account_id=None,
        )
        repo = KnowledgeRepository(db)
        profile = repo.get_ea_profile_by_ea_key("magic-11")
        assert profile is not None
        rows = repo.list_evidence_for_ea(profile.id)
        assert len(rows) == 1
        assert rows[0].account_id is None
        assert repo.list_ea_profile_ids_with_evidence_for_account("anything") == []


def test_file_ingest_stores_explicit_account_id():
    with tempfile.TemporaryDirectory() as tmp:
        deals = Path(tmp) / "deals.json"
        deals.write_text(
            json.dumps(
                [
                    {
                        "ticket": 2,
                        "magic": 22,
                        "symbol": "XAUUSD",
                        "profit": 1.0,
                        "swap": 0,
                        "commission": 0,
                        "time": "2026-08-01T10:00:00+00:00",
                    }
                ]
            ),
            encoding="utf-8",
        )
        db = str(Path(tmp) / "knowledge.db")
        run_file_ingest(
            file_path=deals,
            db_path=db,
            limit=10,
            account_type="demo",
            account_id="acc-file",
        )
        repo = KnowledgeRepository(db)
        profile = repo.get_ea_profile_by_ea_key("magic-22")
        assert profile is not None
        rows = repo.list_evidence_for_ea(profile.id)
        assert rows[0].account_id == "acc-file"
        assert repo.list_ea_profile_ids_with_evidence_for_account("acc-file") == [
            profile.id
        ]

"""Structural tests for evidence provenance fields."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, EvidenceItem
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


def _minimal_profile(profile_id):
    return EAKnowledgeProfile(
        id=profile_id,
        ea_key="test-ea",
        name="Test EA",
        version="1.0.0",
        purpose="test",
        entry_rules="n/a",
        exit_rules="n/a",
        risk_rules={},
        permitted_symbols=["XAUUSD"],
        permitted_sessions=["London"],
        market_conditions={},
    )


def test_default_provenance_is_manual():
    item = EvidenceItem(
        id=uuid4(),
        ea_profile_id=uuid4(),
        evidence_type="trade",
        occurred_at=datetime.now(timezone.utc),
        symbol="XAUUSD",
    )
    assert item.source_system == "manual"
    assert item.external_id is None
    assert item.ingestion_batch_id is None


def test_provenance_roundtrip_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        repo = KnowledgeRepository(Path(tmp) / "knowledge.db")
        profile_id = uuid4()
        repo.save_ea_profile(_minimal_profile(profile_id))
        item = EvidenceItem(
            id=uuid4(),
            ea_profile_id=profile_id,
            evidence_type="trade",
            occurred_at=datetime.now(timezone.utc),
            symbol="XAUUSD",
            source_system="mt5_bridge",
            external_id="ticket-12345",
            ingestion_batch_id="batch-2026-07-14",
        )
        repo.save_evidence(item)
        loaded = repo.get_evidence(item.id)
        assert loaded is not None
        assert loaded.source_system == "mt5_bridge"
        assert loaded.external_id == "ticket-12345"
        assert loaded.ingestion_batch_id == "batch-2026-07-14"


def test_schema_version_is_at_least_two():
    with tempfile.TemporaryDirectory() as tmp:
        repo = KnowledgeRepository(Path(tmp) / "knowledge.db")
        assert repo._schema_version() >= 2

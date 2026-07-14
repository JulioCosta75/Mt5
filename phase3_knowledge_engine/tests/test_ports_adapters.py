"""Structural tests for domain ports and ingestion adapter stubs."""

import tempfile
from pathlib import Path

from phase3_knowledge_engine.adapters.ingestion.stub_evidence_source import StubEvidenceSource
from phase3_knowledge_engine.domain.ports.evidence_source import EvidenceSourcePort
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


def test_sqlite_repository_satisfies_repository_port():
    with tempfile.TemporaryDirectory() as tmp:
        repo = KnowledgeRepository(Path(tmp) / "knowledge.db")
        assert isinstance(repo, KnowledgeRepositoryPort)


def test_stub_evidence_source_satisfies_port():
    source = StubEvidenceSource()
    assert isinstance(source, EvidenceSourcePort)
    assert source.source_system == "stub"
    assert source.fetch_pending() == []

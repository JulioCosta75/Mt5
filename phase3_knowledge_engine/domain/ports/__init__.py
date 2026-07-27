"""Domain ports — contracts for infrastructure and adapters."""

from phase3_knowledge_engine.domain.ports.evidence_source import EvidenceSourcePort
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort

__all__ = ["EvidenceSourcePort", "KnowledgeRepositoryPort"]

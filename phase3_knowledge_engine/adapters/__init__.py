"""Ingestion adapters — external data sources into EvidenceItem."""

from phase3_knowledge_engine.adapters.ingestion.mt5_bridge_evidence_source import (
    Mt5BridgeEvidenceSource,
)
from phase3_knowledge_engine.adapters.ingestion.stub_evidence_source import StubEvidenceSource

__all__ = ["StubEvidenceSource", "Mt5BridgeEvidenceSource"]

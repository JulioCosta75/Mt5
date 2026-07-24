"""Atlas Phase 3 — Knowledge Management Engine (isolated foundation).

This package is intentionally NOT imported by Phase 2 runtime code.
Enable only via PHASE3_KNOWLEDGE_ENGINE_ENABLED after Phase 2 validation.
"""

from phase3_knowledge_engine.config import PHASE3_KNOWLEDGE_ENGINE_ENABLED

__all__ = ["PHASE3_KNOWLEDGE_ENGINE_ENABLED"]

"""Atlas Phase 3 — Knowledge Management Engine (isolated foundation).

This package is imported by Phase 2 only for the flag-gated
``/api/knowledge/v1`` read-only routes (Gate 5 Stage 2). Those routes
return 404 unless ``PHASE3_KNOWLEDGE_ENGINE_ENABLED`` is true.
"""

from phase3_knowledge_engine.config import PHASE3_KNOWLEDGE_ENGINE_ENABLED

__all__ = ["PHASE3_KNOWLEDGE_ENGINE_ENABLED"]

"""Phase 3 configuration — isolated from Phase 2 backend settings."""

from __future__ import annotations

import os

# Single source of truth. Phase 2 must never read this flag in production until
# an explicit integration gate is passed.
PHASE3_KNOWLEDGE_ENGINE_ENABLED: bool = (
    os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower() in ("1", "true", "yes")
)

# Default SQLite database file (separate from atlas.db).
DEFAULT_KNOWLEDGE_DB_PATH: str = os.environ.get(
    "PHASE3_KNOWLEDGE_DB_PATH", "knowledge.db"
)

# Minimum similar observations required to form a RepeatedPattern.
# Configurable; never sufficient on its own for validation.
MIN_OBSERVATIONS_FOR_PATTERN: int = int(
    os.environ.get("PHASE3_MIN_OBSERVATIONS_FOR_PATTERN", "2")
)

# Minimum evidence count required to promote KnowledgeCandidate → Knowledge.
# Configurable via environment; human review and other Rule 6 criteria still apply.
MIN_EVIDENCE_FOR_KNOWLEDGE: int = int(
    os.environ.get("PHASE3_MIN_EVIDENCE_FOR_KNOWLEDGE", "10")
)

# Minimum sample size required to promote KnowledgeCandidate → Knowledge.
# Configurable via environment; human review and other Rule 6 criteria still apply.
MIN_SAMPLE_FOR_KNOWLEDGE: int = int(
    os.environ.get("PHASE3_MIN_SAMPLE_FOR_KNOWLEDGE", "30")
)

"""Atlas Educador — isolated static glossary (Revolution AI Stage 1).

This package is **not** imported by Phase 2. No HTTP routes. No LLM.
No account or user data. Content is generic and identical for everyone.
"""

from education.catalog import REQUIRED_CONCEPT_IDS, get_explanation, list_concept_ids
from education.domain.entities import Explanation

__all__ = [
    "Explanation",
    "REQUIRED_CONCEPT_IDS",
    "get_explanation",
    "list_concept_ids",
]

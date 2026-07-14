"""Phase 3 domain layer — pure business rules, no Phase 2 imports."""

from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    EvidenceItem,
    KnowledgeRecord,
    MarketContext,
)
from phase3_knowledge_engine.domain.rules import (
    KNOWLEDGE_PRINCIPLE,
    DomainRuleViolation,
    assert_can_promote_to_knowledge,
    assert_hypothesis_explicit,
    assert_single_observation_not_knowledge,
)
from phase3_knowledge_engine.domain.validation_states import (
    HUMAN_REVIEW_REQUIRED_TARGETS,
    ValidationState,
    allowed_transitions,
    requires_human_review,
)

__all__ = [
    "AuditTrailEntry",
    "EAKnowledgeProfile",
    "EvidenceItem",
    "KnowledgeRecord",
    "MarketContext",
    "KNOWLEDGE_PRINCIPLE",
    "DomainRuleViolation",
    "ValidationState",
    "HUMAN_REVIEW_REQUIRED_TARGETS",
    "allowed_transitions",
    "requires_human_review",
    "assert_can_promote_to_knowledge",
    "assert_hypothesis_explicit",
    "assert_single_observation_not_knowledge",
]

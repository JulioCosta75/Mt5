"""Domain rules — epistemic guardrails for Phase 3 knowledge."""

from __future__ import annotations

from phase3_knowledge_engine.config import (
    MIN_EVIDENCE_FOR_KNOWLEDGE,
    MIN_OBSERVATIONS_FOR_PATTERN,
    MIN_SAMPLE_FOR_KNOWLEDGE,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState

KNOWLEDGE_PRINCIPLE = (
    "Knowledge is not what happened. Knowledge is what survived validation."
)

KNOWLEDGE_TERMINAL_STATES = frozenset({
    ValidationState.KNOWLEDGE,
})

KNOWLEDGE_PATH_STATES = frozenset({
    ValidationState.FULLY_VALIDATED_CONCLUSION,
    ValidationState.KNOWLEDGE_CANDIDATE,
    ValidationState.KNOWLEDGE,
})


class DomainRuleViolation(ValueError):
    """Raised when a knowledge lifecycle rule would be broken."""


def assert_single_observation_not_knowledge(
    observation_count: int,
    target_state: ValidationState,
) -> None:
    """Rule 1: a single observation must never become knowledge."""
    if observation_count < 1:
        raise DomainRuleViolation("At least one observation is required.")
    if observation_count == 1 and target_state in KNOWLEDGE_PATH_STATES:
        raise DomainRuleViolation(
            f"{KNOWLEDGE_PRINCIPLE} "
            "A single observation cannot reach conclusion or knowledge states."
        )
    if observation_count == 1 and target_state is ValidationState.HYPOTHESIS:
        raise DomainRuleViolation(
            "A single observation cannot form a Hypothesis (Rule 3)."
        )


def assert_repeated_pattern_threshold(
    similar_observation_count: int,
    *,
    min_required: int | None = None,
) -> None:
    """Rule 2: RepeatedPattern requires configurable minimum similar observations."""
    threshold = min_required if min_required is not None else MIN_OBSERVATIONS_FOR_PATTERN
    if similar_observation_count < threshold:
        raise DomainRuleViolation(
            f"RepeatedPattern requires at least {threshold} similar observations "
            f"within comparable context (found {similar_observation_count}). "
            "This threshold is never sufficient validation on its own."
        )


def assert_hypothesis_explicit(
    *,
    explicit: bool,
    from_state: ValidationState,
) -> None:
    """Rule 3: Hypothesis creation is always an explicit human act."""
    if not explicit:
        raise DomainRuleViolation(
            "Hypothesis must be created explicitly; never auto-generated from a single trade."
        )
    if from_state is not ValidationState.REPEATED_PATTERN:
        raise DomainRuleViolation(
            f"Hypothesis can only be created explicitly from RepeatedPattern, not {from_state.value}."
        )


def assert_human_review_for_promotion(
    target_state: ValidationState,
    *,
    human_review_recorded: bool,
    reviewer: str | None,
) -> None:
    """Rules 4–6: human review required for validation milestones."""
    from phase3_knowledge_engine.domain.validation_states import requires_human_review

    if not requires_human_review(target_state):
        return
    if not human_review_recorded or not reviewer:
        raise DomainRuleViolation(
            f"Transition to {target_state.value} requires recorded human review."
        )


def assert_can_promote_to_knowledge(
    *,
    relevance_for_decisions: str | None,
    evidence_count: int,
    sample_size: int,
    context_documented: bool,
    human_review_recorded: bool,
    reviewer: str | None,
    material_contradictions_resolved: bool,
    min_evidence: int | None = None,
    min_sample: int | None = None,
) -> None:
    """Rule 6: Knowledge promotion criteria."""
    evidence_threshold = (
        min_evidence if min_evidence is not None else MIN_EVIDENCE_FOR_KNOWLEDGE
    )
    sample_threshold = (
        min_sample if min_sample is not None else MIN_SAMPLE_FOR_KNOWLEDGE
    )
    assert_human_review_for_promotion(
        ValidationState.KNOWLEDGE,
        human_review_recorded=human_review_recorded,
        reviewer=reviewer,
    )
    if not relevance_for_decisions:
        raise DomainRuleViolation(
            "Knowledge promotion requires documented relevance for future decisions."
        )
    if evidence_count < evidence_threshold:
        raise DomainRuleViolation(
            f"Insufficient evidence for Knowledge (need >={evidence_threshold}, got {evidence_count})."
        )
    if sample_size < sample_threshold:
        raise DomainRuleViolation(
            f"Insufficient sample size for Knowledge (need >={sample_threshold}, got {sample_size})."
        )
    if not context_documented:
        raise DomainRuleViolation("Knowledge promotion requires documented context.")
    if not material_contradictions_resolved:
        raise DomainRuleViolation(
            "Unresolved material contradictions block Knowledge promotion."
        )


def assert_no_silent_knowledge_rewrite(impact: str) -> None:
    """Rule 7: existing knowledge may only be affected via explicit impact types."""
    allowed = {"confirm", "weaken", "review", "invalidate"}
    if impact not in allowed:
        raise DomainRuleViolation(
            f"Evidence impact must be one of {sorted(allowed)}, not {impact!r}."
        )


def assert_invalidated_preserved(action: str) -> None:
    """Rule 8: invalidated conclusions are never deleted."""
    if action == "delete":
        raise DomainRuleViolation(
            "InvalidatedConclusion records must be preserved as historical refutations."
        )

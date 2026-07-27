"""Validation state machine for the Phase 3 knowledge lifecycle."""

from __future__ import annotations

from enum import Enum


class ValidationState(str, Enum):
    RAW_OBSERVATION = "raw_observation"
    REPEATED_PATTERN = "repeated_pattern"
    HYPOTHESIS = "hypothesis"
    EVIDENCE_UNDER_REVIEW = "evidence_under_review"
    PROVISIONALLY_VALIDATED_CONCLUSION = "provisionally_validated_conclusion"
    FULLY_VALIDATED_CONCLUSION = "fully_validated_conclusion"
    KNOWLEDGE_CANDIDATE = "knowledge_candidate"
    KNOWLEDGE = "knowledge"
    INVALIDATED_CONCLUSION = "invalidated_conclusion"


# States that MUST NOT be reached without a recorded human review.
HUMAN_REVIEW_REQUIRED_TARGETS: frozenset[ValidationState] = frozenset({
    ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
    ValidationState.FULLY_VALIDATED_CONCLUSION,
    ValidationState.KNOWLEDGE_CANDIDATE,
    ValidationState.KNOWLEDGE,
    ValidationState.INVALIDATED_CONCLUSION,
})


# Directed edges: from_state -> {to_state, ...}
_TRANSITIONS: dict[ValidationState, frozenset[ValidationState]] = {
    ValidationState.RAW_OBSERVATION: frozenset({
        ValidationState.REPEATED_PATTERN,
        ValidationState.RAW_OBSERVATION,
    }),
    ValidationState.REPEATED_PATTERN: frozenset({
        ValidationState.HYPOTHESIS,
        ValidationState.RAW_OBSERVATION,
    }),
    ValidationState.HYPOTHESIS: frozenset({
        ValidationState.EVIDENCE_UNDER_REVIEW,
        ValidationState.INVALIDATED_CONCLUSION,
    }),
    ValidationState.EVIDENCE_UNDER_REVIEW: frozenset({
        ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
        ValidationState.INVALIDATED_CONCLUSION,
        ValidationState.HYPOTHESIS,
    }),
    ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION: frozenset({
        ValidationState.FULLY_VALIDATED_CONCLUSION,
        ValidationState.EVIDENCE_UNDER_REVIEW,
        ValidationState.INVALIDATED_CONCLUSION,
    }),
    ValidationState.FULLY_VALIDATED_CONCLUSION: frozenset({
        ValidationState.KNOWLEDGE_CANDIDATE,
        ValidationState.EVIDENCE_UNDER_REVIEW,
        ValidationState.INVALIDATED_CONCLUSION,
    }),
    ValidationState.KNOWLEDGE_CANDIDATE: frozenset({
        ValidationState.KNOWLEDGE,
        ValidationState.EVIDENCE_UNDER_REVIEW,
        ValidationState.INVALIDATED_CONCLUSION,
    }),
    ValidationState.KNOWLEDGE: frozenset({
        ValidationState.EVIDENCE_UNDER_REVIEW,
    }),
    ValidationState.INVALIDATED_CONCLUSION: frozenset(),
}


def allowed_transitions(from_state: ValidationState) -> frozenset[ValidationState]:
    return _TRANSITIONS.get(from_state, frozenset())


def requires_human_review(to_state: ValidationState) -> bool:
    return to_state in HUMAN_REVIEW_REQUIRED_TARGETS


def can_transition(
    from_state: ValidationState,
    to_state: ValidationState,
    *,
    human_review_recorded: bool,
) -> bool:
    if to_state not in allowed_transitions(from_state):
        return False
    if requires_human_review(to_state) and not human_review_recorded:
        return False
    # FullyValidatedConclusion must pass through KnowledgeCandidate before Knowledge.
    if to_state is ValidationState.KNOWLEDGE:
        return from_state is ValidationState.KNOWLEDGE_CANDIDATE
    if to_state is ValidationState.KNOWLEDGE_CANDIDATE:
        return from_state is ValidationState.FULLY_VALIDATED_CONCLUSION
    return True

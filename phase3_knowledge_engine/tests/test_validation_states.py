"""Unit tests for validation state machine."""

import pytest

from phase3_knowledge_engine.domain.validation_states import (
    ValidationState,
    allowed_transitions,
    can_transition,
    requires_human_review,
)


class TestHumanReviewRequired:
    @pytest.mark.parametrize("state", [
        ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
        ValidationState.FULLY_VALIDATED_CONCLUSION,
        ValidationState.KNOWLEDGE_CANDIDATE,
        ValidationState.KNOWLEDGE,
        ValidationState.INVALIDATED_CONCLUSION,
    ])
    def test_milestone_states_require_review(self, state):
        assert requires_human_review(state)


class TestTransitionGuards:
    def test_raw_to_repeated_allowed_without_review(self):
        assert can_transition(
            ValidationState.RAW_OBSERVATION,
            ValidationState.REPEATED_PATTERN,
            human_review_recorded=False,
        )

    def test_provisional_requires_human_review(self):
        assert not can_transition(
            ValidationState.EVIDENCE_UNDER_REVIEW,
            ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
            human_review_recorded=False,
        )
        assert can_transition(
            ValidationState.EVIDENCE_UNDER_REVIEW,
            ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
            human_review_recorded=True,
        )

    def test_fully_validated_cannot_skip_to_knowledge(self):
        assert not can_transition(
            ValidationState.FULLY_VALIDATED_CONCLUSION,
            ValidationState.KNOWLEDGE,
            human_review_recorded=True,
        )

    def test_knowledge_only_from_candidate(self):
        assert can_transition(
            ValidationState.KNOWLEDGE_CANDIDATE,
            ValidationState.KNOWLEDGE,
            human_review_recorded=True,
        )
        assert not can_transition(
            ValidationState.FULLY_VALIDATED_CONCLUSION,
            ValidationState.KNOWLEDGE_CANDIDATE,
            human_review_recorded=False,
        )

    def test_knowledge_candidate_only_from_fully_validated(self):
        assert can_transition(
            ValidationState.FULLY_VALIDATED_CONCLUSION,
            ValidationState.KNOWLEDGE_CANDIDATE,
            human_review_recorded=True,
        )

    def test_invalidated_is_terminal(self):
        assert allowed_transitions(ValidationState.INVALIDATED_CONCLUSION) == frozenset()

    def test_knowledge_reopens_to_review_only(self):
        assert can_transition(
            ValidationState.KNOWLEDGE,
            ValidationState.EVIDENCE_UNDER_REVIEW,
            human_review_recorded=True,
        )

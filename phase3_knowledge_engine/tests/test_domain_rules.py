"""Unit tests for Phase 3 domain rules."""

import pytest

from phase3_knowledge_engine.domain.rules import (
    KNOWLEDGE_PRINCIPLE,
    DomainRuleViolation,
    assert_can_promote_to_knowledge,
    assert_hypothesis_explicit,
    assert_invalidated_preserved,
    assert_no_silent_knowledge_rewrite,
    assert_repeated_pattern_threshold,
    assert_single_observation_not_knowledge,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState


class TestKnowledgePrinciple:
    def test_principle_is_codified_in_rules_module(self):
        assert KNOWLEDGE_PRINCIPLE == (
            "Knowledge is not what happened. Knowledge is what survived validation."
        )


class TestSingleObservationRule:
    def test_one_observation_cannot_reach_knowledge(self):
        with pytest.raises(DomainRuleViolation, match="single observation"):
            assert_single_observation_not_knowledge(1, ValidationState.KNOWLEDGE)

    def test_one_observation_cannot_form_hypothesis(self):
        with pytest.raises(DomainRuleViolation, match="Hypothesis"):
            assert_single_observation_not_knowledge(1, ValidationState.HYPOTHESIS)

    def test_two_observations_may_progress_past_raw(self):
        assert_single_observation_not_knowledge(2, ValidationState.REPEATED_PATTERN)


class TestRepeatedPatternThreshold:
    def test_default_minimum_is_two(self):
        assert_repeated_pattern_threshold(2)

    def test_one_is_insufficient(self):
        with pytest.raises(DomainRuleViolation, match="at least 2"):
            assert_repeated_pattern_threshold(1)

    def test_threshold_is_configurable(self):
        assert_repeated_pattern_threshold(5, min_required=5)


class TestHypothesisExplicit:
    def test_must_be_explicit(self):
        with pytest.raises(DomainRuleViolation, match="explicit"):
            assert_hypothesis_explicit(explicit=False, from_state=ValidationState.REPEATED_PATTERN)

    def test_only_from_repeated_pattern(self):
        with pytest.raises(DomainRuleViolation, match="RepeatedPattern"):
            assert_hypothesis_explicit(explicit=True, from_state=ValidationState.RAW_OBSERVATION)

    def test_valid_explicit_hypothesis(self):
        assert_hypothesis_explicit(explicit=True, from_state=ValidationState.REPEATED_PATTERN)


class TestKnowledgePromotion:
    def test_default_thresholds_match_config(self):
        from phase3_knowledge_engine.config import (
            MIN_EVIDENCE_FOR_KNOWLEDGE,
            MIN_SAMPLE_FOR_KNOWLEDGE,
        )

        assert MIN_EVIDENCE_FOR_KNOWLEDGE == 10
        assert MIN_SAMPLE_FOR_KNOWLEDGE == 30

    def test_requires_all_criteria(self):
        assert_can_promote_to_knowledge(
            relevance_for_decisions="Position sizing for London session",
            evidence_count=10,
            sample_size=30,
            context_documented=True,
            human_review_recorded=True,
            reviewer="analyst@forge",
            material_contradictions_resolved=True,
        )

    def test_blocks_at_default_evidence_boundary(self):
        with pytest.raises(DomainRuleViolation, match="Insufficient evidence"):
            assert_can_promote_to_knowledge(
                relevance_for_decisions="Position sizing for London session",
                evidence_count=9,
                sample_size=30,
                context_documented=True,
                human_review_recorded=True,
                reviewer="analyst@forge",
                material_contradictions_resolved=True,
            )

    def test_blocks_at_default_sample_boundary(self):
        with pytest.raises(DomainRuleViolation, match="Insufficient sample size"):
            assert_can_promote_to_knowledge(
                relevance_for_decisions="Position sizing for London session",
                evidence_count=10,
                sample_size=29,
                context_documented=True,
                human_review_recorded=True,
                reviewer="analyst@forge",
                material_contradictions_resolved=True,
            )

    def test_blocks_without_relevance(self):
        with pytest.raises(DomainRuleViolation, match="relevance"):
            assert_can_promote_to_knowledge(
                relevance_for_decisions=None,
                evidence_count=10,
                sample_size=30,
                context_documented=True,
                human_review_recorded=True,
                reviewer="analyst",
                material_contradictions_resolved=True,
            )


class TestEvidenceImpact:
    def test_silent_rewrite_forbidden(self):
        with pytest.raises(DomainRuleViolation):
            assert_no_silent_knowledge_rewrite("overwrite")

    def test_allowed_impacts(self):
        for impact in ("confirm", "weaken", "review", "invalidate"):
            assert_no_silent_knowledge_rewrite(impact)


class TestInvalidatedPreservation:
    def test_delete_forbidden(self):
        with pytest.raises(DomainRuleViolation, match="preserved"):
            assert_invalidated_preserved("delete")

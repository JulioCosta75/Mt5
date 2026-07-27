"""Unit tests for advisory confidence scoring."""

from phase3_knowledge_engine.domain.confidence import (
    THRESHOLD_FULL,
    THRESHOLD_PROVISIONAL,
    compute_confidence,
    consistency_ratio,
    sample_score,
)


class TestConfidenceScoring:
    def test_zero_sample_yields_zero(self):
        assert sample_score(0) == 0.0

    def test_large_sample_approaches_one(self):
        assert sample_score(100) > 0.95

    def test_consistency_all_supporting(self):
        assert consistency_ratio(10, 0) == 1.0

    def test_confidence_bounded(self):
        score = compute_confidence(
            sample_size=25,
            supporting_count=20,
            contradictory_count=5,
            days_since_last_evidence=10,
            context_filled=4,
            context_total=5,
        )
        assert 0.0 <= score <= 1.0

    def test_thresholds_documented(self):
        assert THRESHOLD_PROVISIONAL < THRESHOLD_FULL

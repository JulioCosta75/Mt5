"""Deterministic confidence scoring — advisory only, never replaces human review."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceWeights:
    sample: float = 0.35
    consistency: float = 0.30
    recency: float = 0.15
    context: float = 0.20


def sample_score(n: int, midpoint: float = 15.0, steepness: float = 0.25) -> float:
    """Sigmoid-like score: low for small n, approaches 1.0 for large samples."""
    if n <= 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-steepness * (n - midpoint)))


def consistency_ratio(supporting: int, contradictory: int) -> float:
    total = supporting + contradictory
    if total == 0:
        return 0.0
    return supporting / total


def recency_decay(days_since_last_evidence: int, half_life_days: float = 90.0) -> float:
    if days_since_last_evidence < 0:
        days_since_last_evidence = 0
    return 0.5 ** (days_since_last_evidence / half_life_days)


def context_coverage(filled_fields: int, total_fields: int) -> float:
    if total_fields <= 0:
        return 0.0
    return min(1.0, filled_fields / total_fields)


def compute_confidence(
    *,
    sample_size: int,
    supporting_count: int,
    contradictory_count: int,
    days_since_last_evidence: int,
    context_filled: int,
    context_total: int,
    weights: ConfidenceWeights | None = None,
) -> float:
    """Return a 0.0–1.0 advisory score. Does NOT authorize automatic promotion."""
    w = weights or ConfidenceWeights()
    raw = (
        w.sample * sample_score(sample_size)
        + w.consistency * consistency_ratio(supporting_count, contradictory_count)
        + w.recency * recency_decay(days_since_last_evidence)
        + w.context * context_coverage(context_filled, context_total)
    )
    return round(min(1.0, max(0.0, raw)), 4)


# Advisory thresholds documented in CONFIDENCE_SCORING.md
THRESHOLD_PROVISIONAL = 0.55
THRESHOLD_FULL = 0.75

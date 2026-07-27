"""Tests for Phase 3 configuration — defaults and environment overrides."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from phase3_knowledge_engine.config import (
    MIN_EVIDENCE_FOR_KNOWLEDGE,
    MIN_SAMPLE_FOR_KNOWLEDGE,
    PHASE3_KNOWLEDGE_ENGINE_ENABLED,
)


class TestConfigDefaults:
    def test_feature_flag_off_by_default(self):
        assert PHASE3_KNOWLEDGE_ENGINE_ENABLED is False

    def test_knowledge_promotion_defaults(self):
        assert MIN_EVIDENCE_FOR_KNOWLEDGE == 10
        assert MIN_SAMPLE_FOR_KNOWLEDGE == 30


class TestKnowledgeThresholdConfigurability:
    def test_thresholds_change_via_environment_without_domain_edits(self):
        """Prove env overrides work in a fresh interpreter without editing domain code."""
        script = """
from phase3_knowledge_engine.config import (
    MIN_EVIDENCE_FOR_KNOWLEDGE,
    MIN_SAMPLE_FOR_KNOWLEDGE,
)
from phase3_knowledge_engine.domain.rules import (
    DomainRuleViolation,
    assert_can_promote_to_knowledge,
)

assert MIN_EVIDENCE_FOR_KNOWLEDGE == 5
assert MIN_SAMPLE_FOR_KNOWLEDGE == 15

assert_can_promote_to_knowledge(
    relevance_for_decisions="Session routing",
    evidence_count=5,
    sample_size=15,
    context_documented=True,
    human_review_recorded=True,
    reviewer="analyst@forge",
    material_contradictions_resolved=True,
)

try:
    assert_can_promote_to_knowledge(
        relevance_for_decisions="Session routing",
        evidence_count=4,
        sample_size=15,
        context_documented=True,
        human_review_recorded=True,
        reviewer="analyst@forge",
        material_contradictions_resolved=True,
    )
except DomainRuleViolation:
    pass
else:
    raise SystemExit("expected evidence threshold violation")

try:
    assert_can_promote_to_knowledge(
        relevance_for_decisions="Session routing",
        evidence_count=5,
        sample_size=14,
        context_documented=True,
        human_review_recorded=True,
        reviewer="analyst@forge",
        material_contradictions_resolved=True,
    )
except DomainRuleViolation:
    pass
else:
    raise SystemExit("expected sample threshold violation")
"""
        env = os.environ.copy()
        env["PHASE3_MIN_EVIDENCE_FOR_KNOWLEDGE"] = "5"
        env["PHASE3_MIN_SAMPLE_FOR_KNOWLEDGE"] = "15"
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout

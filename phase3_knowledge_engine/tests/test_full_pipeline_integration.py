"""End-to-end integration across Phase 3 Blocks 1–6 (temp SQLite only).

Proves the real pipeline wiring:
  map_deal_to_evidence → ingest_grouped_observation → review queue →
  human hypothesis/review → KNOWLEDGE → technical report,
plus EA version change → quarantine → human confirm.

Does not require or toggle PHASE3_KNOWLEDGE_ENGINE_ENABLED.
No network / no live MT5 bridge.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from phase3_knowledge_engine.adapters.ingestion.mt5_bridge_evidence_source import (
    SOURCE_SYSTEM,
    map_deal_to_evidence,
)
from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.config import (
    MIN_EVIDENCE_FOR_KNOWLEDGE,
    MIN_OBSERVATIONS_FOR_PATTERN,
    MIN_SAMPLE_FOR_KNOWLEDGE,
    PHASE3_KNOWLEDGE_ENGINE_ENABLED,
)
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, MarketContext
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.report import build_technical_report


EA_VERSION = "2.1.0"
EA_KEY = "london-scalper"
SESSION = "London"
SYMBOL = "XAUUSD"
HYPOTHESIS_STATEMENT = (
    "London-session XAUUSD entries outperform after spread filter"
)


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "knowledge.db"
        repo = KnowledgeRepository(db)
        yield KnowledgeEngineService(repo)


def _register_ea(engine: KnowledgeEngineService) -> EAKnowledgeProfile:
    return engine.register_ea_profile(
        EAKnowledgeProfile(
            id=uuid4(),
            ea_key=EA_KEY,
            name="London Scalper",
            version=EA_VERSION,
            purpose="Capture London open momentum on XAUUSD",
            entry_rules="Break of Asian range high with spread filter",
            exit_rules="Fixed RR 1:1.5 or session end",
            risk_rules={"max_daily_loss_pct": 2.0},
            permitted_symbols=[SYMBOL],
            permitted_sessions=[SESSION],
            market_conditions={"preferred_regime": "trending"},
            status="active",
        )
    )


def _fake_deal(*, ticket: int, profit: float) -> dict:
    """Realistic MT5 bridge GET /deals-shaped dict (no network)."""
    return {
        "ticket": ticket,
        "order": ticket - 1000,
        "position_id": ticket - 2000,
        "symbol": SYMBOL,
        "side": "BUY",
        "volume": 0.1,
        "price": 2400.5 + (ticket % 10) * 0.1,
        "profit": profit,
        "swap": -0.2,
        "commission": -0.3,
        "magic": 424242,
        "comment": "london-scalper",
        "time": f"2026-08-{10 + (ticket % 5):02d}T08:15:00+00:00",
    }


def _map_deal_for_pipeline(deal: dict, ea_profile_id) -> object:
    """Block 1 mapping, then attach version/session used by Block 2 grouping.

    Bridge deal payloads do not carry session/ea_version; those come from the
    registered EA dossier + known trading session for this integration path.
    """
    item = map_deal_to_evidence(
        deal,
        ea_profile_id=ea_profile_id,
        account_type="demo",
        ingestion_batch_id="e2e-pipeline-batch",
    )
    assert item.source_system == SOURCE_SYSTEM
    assert item.external_id == str(deal["ticket"])
    assert item.symbol == SYMBOL
    item.ea_version = EA_VERSION
    item.session = SESSION
    item.context = MarketContext(
        session=SESSION,
        symbol=SYMBOL,
        occurred_at=item.occurred_at,
    )
    return item


def _assert_flag_still_off() -> None:
    assert PHASE3_KNOWLEDGE_ENGINE_ENABLED is False
    env = os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower()
    assert env not in ("1", "true", "yes")


def test_full_pipeline_blocks_1_through_6(engine: KnowledgeEngineService):
    _assert_flag_still_off()

    # --- Register EA dossier -------------------------------------------------
    profile = _register_ea(engine)
    assert profile.status == "active"
    assert profile.version == EA_VERSION
    _assert_flag_still_off()

    # --- Block 1 → Block 2: real deal mapping + grouped ingest ---------------
    assert MIN_OBSERVATIONS_FOR_PATTERN == 2
    deal_count = MIN_OBSERVATIONS_FOR_PATTERN + 1  # enough to cross threshold
    last_record = None
    for i in range(deal_count):
        deal = _fake_deal(ticket=90001 + i, profit=10.0 + i)
        evidence = _map_deal_for_pipeline(deal, profile.id)
        last_record = engine.ingest_grouped_observation(evidence)

    assert last_record is not None
    assert last_record.validation_state == ValidationState.REPEATED_PATTERN.value
    assert last_record.sample_size >= MIN_OBSERVATIONS_FOR_PATTERN
    assert last_record.ea_profile_id == profile.id
    expected_sig = KnowledgeEngineService.compute_context_signature(
        profile.id, EA_VERSION, SESSION, SYMBOL
    )
    assert last_record.context_signature == expected_sig
    _assert_flag_still_off()

    # --- Block 3: find pending record via list (do not hardcode ID) ----------
    pending = engine.repo.list_knowledge_records_by_state(
        ValidationState.REPEATED_PATTERN,
        ea_profile_id=profile.id,
    )
    assert len(pending) == 1
    pattern_record = pending[0]
    assert pattern_record.id == last_record.id
    assert pattern_record.validation_state == ValidationState.REPEATED_PATTERN.value

    # --- Explicit human hypothesis (never automatic) -------------------------
    record = engine.create_hypothesis(
        pattern_record.id,
        statement=HYPOTHESIS_STATEMENT,
        actor="analyst@forge",
        justification="Explicit hypothesis after repeated London pattern.",
    )
    assert record.validation_state == ValidationState.HYPOTHESIS.value
    assert record.statement == HYPOTHESIS_STATEMENT
    _assert_flag_still_off()

    # --- Human review path through to KNOWLEDGE (Rule 6) ---------------------
    review_evidence_ids = list(record.supporting_evidence_ids) or [uuid4(), uuid4()]
    record = engine.submit_for_review(
        record.id,
        actor="analyst@forge",
        justification="Evidence package submitted for London edge review.",
        evidence_ids=review_evidence_ids,
    )
    assert record.validation_state == ValidationState.EVIDENCE_UNDER_REVIEW.value

    # Satisfy Rule 6 thresholds (ingest only proved pattern grouping, not sample).
    record.sample_size = max(record.sample_size, MIN_SAMPLE_FOR_KNOWLEDGE)
    record.evidence_count = max(record.evidence_count, MIN_EVIDENCE_FOR_KNOWLEDGE)
    record.date_range_start = datetime(2026, 1, 1, tzinfo=timezone.utc).date()
    record.date_range_end = datetime(2026, 8, 20, tzinfo=timezone.utc).date()
    engine.repo.save_knowledge_record(record)

    for state in (
        ValidationState.PROVISIONALLY_VALIDATED_CONCLUSION,
        ValidationState.FULLY_VALIDATED_CONCLUSION,
        ValidationState.KNOWLEDGE_CANDIDATE,
    ):
        record = engine.apply_human_review_transition(
            record.id,
            state,
            actor="lead@forge",
            justification=f"Human review approving {state.value}",
            context_documented=True,
        )
    assert record.validation_state == ValidationState.KNOWLEDGE_CANDIDATE.value

    record = engine.apply_human_review_transition(
        record.id,
        ValidationState.KNOWLEDGE,
        actor="lead@forge",
        justification="Promoted to knowledge after full validation.",
        relevance_for_decisions="Session allocation for XAUUSD London EAs",
        context_documented=True,
        material_contradictions_resolved=True,
    )
    assert record.validation_state == ValidationState.KNOWLEDGE.value
    assert record.confidence_score > 0.0
    knowledge_confidence = record.confidence_score
    _assert_flag_still_off()

    # --- Block 6: technical report -------------------------------------------
    report = build_technical_report(profile.id, repository=engine.repo)
    assert HYPOTHESIS_STATEMENT in report
    assert f"ea_key={EA_KEY}" in report
    assert "name=London Scalper" in report
    assert f"version={EA_VERSION}" in report
    assert f"confidence_score: {knowledge_confidence}" in report
    assert f"evidence_count: {record.evidence_count}" in report
    assert f"sample_size: {record.sample_size}" in report
    assert "reviewed_by: lead@forge" in report

    # Earlier states must not invent extra supported conclusions.
    assert "1 supported conclusion" in report
    _assert_flag_still_off()

    # --- Block 4/5: version change → quarantine → human confirm --------------
    saved, change = engine.record_ea_version_change(
        profile.id,
        from_version=EA_VERSION,
        to_version="2.2.0",
        description="Entry filter tightened after London spike losses.",
        actor="analyst@forge",
        effect_summary="Spread filter raised; expected fewer entries.",
    )
    assert saved.status == "quarantine"
    assert saved.version == "2.2.0"
    assert change.from_version == EA_VERSION
    assert change.to_version == "2.2.0"

    quarantined = engine.repo.list_ea_profiles(status="quarantine")
    assert any(p.id == profile.id for p in quarantined)
    assert all(p.status == "quarantine" for p in quarantined)

    cleared = engine.confirm_ea_version_safe(
        profile.id,
        actor="lead@forge",
        justification="Forward demo week clean; human clearance after quarantine.",
    )
    assert cleared.status == "active"
    assert cleared.version == "2.2.0"
    assert engine.repo.list_ea_profiles(status="quarantine") == []
    reloaded = engine.repo.get_ea_profile(profile.id)
    assert reloaded is not None
    assert reloaded.status == "active"

    _assert_flag_still_off()

"""Unit tests for MT5 bridge evidence source (Gate 1 — read-only ingestion)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from phase3_knowledge_engine.adapters.ingestion.mt5_bridge_evidence_source import (
    INCOMPLETE_MARKER,
    SOURCE_SYSTEM,
    Mt5BridgeEvidenceSource,
    deal_net_pnl,
    ensure_ea_profile_for_magic,
    is_incomplete_ea_profile,
    magic_ea_key,
    map_deal_to_evidence,
    resolve_account_type,
)
from phase3_knowledge_engine.domain.ports.evidence_source import EvidenceSourcePort
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


SAMPLE_DEAL = {
    "ticket": 90001,
    "order": 80001,
    "position_id": 70001,
    "symbol": "XAUUSD",
    "side": "BUY",
    "volume": 0.1,
    "price": 2400.5,
    "profit": 12.5,
    "swap": -0.2,
    "commission": -0.3,
    "magic": 424242,
    "comment": "ea-test",
    "time": "2026-08-20T14:30:00+00:00",
}


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def test_mt5_bridge_source_satisfies_port():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        src = Mt5BridgeEvidenceSource(
            repo, fetch_deals=lambda: [], fetch_account=lambda: {}
        )
        assert isinstance(src, EvidenceSourcePort)
        assert src.source_system == "mt5_bridge"
        assert src.fetch_pending() == []


def test_map_deal_pnl_is_profit_plus_swap_plus_commission():
    assert deal_net_pnl(SAMPLE_DEAL) == 12.0  # 12.5 - 0.2 - 0.3
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = ensure_ea_profile_for_magic(repo, 424242)
        item = map_deal_to_evidence(
            SAMPLE_DEAL,
            ea_profile_id=profile.id,
            account_type="demo",
        )
        assert item.evidence_type == "trade"
        assert item.source_system == SOURCE_SYSTEM
        assert item.external_id == "90001"
        assert item.symbol == "XAUUSD"
        assert item.pnl == 12.0
        assert item.account_type == "demo"
        assert item.raw_payload == SAMPLE_DEAL
        assert item.occurred_at.year == 2026
        assert item.occurred_at.month == 8


def test_fetch_pending_maps_mocked_deals():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        src = Mt5BridgeEvidenceSource(
            repo,
            fetch_deals=lambda: [SAMPLE_DEAL],
            fetch_account=lambda: {"server": "PepperstoneUK-Demo"},
        )
        items = src.fetch_pending(limit=10)
        assert len(items) == 1
        item = items[0]
        assert item.pnl == 12.0
        assert item.external_id == "90001"
        assert item.account_type == "demo"
        assert item.source_system == "mt5_bridge"
        profile = repo.get_ea_profile(item.ea_profile_id)
        assert profile is not None
        assert profile.ea_key == magic_ea_key(424242)


def test_idempotency_second_fetch_and_save_skips_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        deals = [SAMPLE_DEAL, {**SAMPLE_DEAL, "ticket": 90002, "profit": 1.0}]

        def fetch():
            return list(deals)

        src = Mt5BridgeEvidenceSource(
            repo,
            fetch_deals=fetch,
            fetch_account=lambda: {"server": "Live-Server"},
        )
        first = src.fetch_pending(limit=50)
        assert len(first) == 2
        for item in first:
            repo.save_evidence(item)

        # Second fetch must not re-offer the same tickets
        second = src.fetch_pending(limit=50)
        assert second == []

        # Saving the same external_id again must not create a second row
        again = map_deal_to_evidence(
            SAMPLE_DEAL,
            ea_profile_id=first[0].ea_profile_id,
            account_type="live",
        )
        stored = repo.save_evidence(again)
        assert stored.id == first[0].id
        # Both deals share magic 424242 → one profile, two evidence rows
        assert first[0].ea_profile_id == first[1].ea_profile_id
        assert repo.count_observations_for_ea(first[0].ea_profile_id) == 2


def test_auto_creates_incomplete_ea_profile_for_unknown_magic():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        assert repo.get_ea_profile_by_ea_key(magic_ea_key(777)) is None
        src = Mt5BridgeEvidenceSource(
            repo,
            fetch_deals=lambda: [{**SAMPLE_DEAL, "ticket": 1, "magic": 777}],
            fetch_account=lambda: {},
        )
        items = src.fetch_pending()
        assert len(items) == 1
        profile = repo.get_ea_profile_by_ea_key(magic_ea_key(777))
        assert profile is not None
        assert is_incomplete_ea_profile(profile)
        assert profile.market_conditions.get("needs_manual_completion") is True
        assert INCOMPLETE_MARKER in profile.known_weaknesses
        assert profile.status == "testing"
        # Second ensure returns same profile (no duplicate ea_key)
        again = ensure_ea_profile_for_magic(repo, 777)
        assert again.id == profile.id


def test_resolve_account_type_from_server_name():
    assert resolve_account_type({"server": "PepperstoneUK-Demo"}) == "demo"
    assert resolve_account_type({"server": "PepperstoneUK-Live"}) == "live"
    assert resolve_account_type({"trade_mode": "DEMO"}) == "demo"

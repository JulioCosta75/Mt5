"""Gate 5 — isolated coincidence of net-negative days between two EAs."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.config import (
    EA_CORRELATION_FLAG_THRESHOLD,
    PHASE3_KNOWLEDGE_ENGINE_ENABLED,
)
from phase3_knowledge_engine.correlation import (
    INSUFFICIENT_LABEL,
    STATUS_INSUFFICIENT,
    STATUS_NOT_PAIRED,
    STATUS_PAIRED,
    coincidence_ratio,
    correlate_ea_pair,
    main,
    negative_pnl_days,
)
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, EvidenceItem
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


AS_OF = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _repo(tmp: str) -> KnowledgeRepository:
    return KnowledgeRepository(Path(tmp) / "knowledge.db")


def _profile(repo: KnowledgeRepository, *, key: str) -> EAKnowledgeProfile:
    return repo.save_ea_profile(
        EAKnowledgeProfile(
            id=uuid4(),
            ea_key=key,
            name=key,
            version="1.0.0",
            purpose="test",
            entry_rules="n/a",
            exit_rules="n/a",
            risk_rules={},
            permitted_symbols=["XAUUSD"],
            permitted_sessions=["London"],
            market_conditions={},
            status="active",
        )
    )


def _trade(
    profile: EAKnowledgeProfile,
    *,
    day_offset: int,
    pnl: float,
    ticket: str,
) -> EvidenceItem:
    occurred = AS_OF - timedelta(days=day_offset)
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=profile.id,
        evidence_type="trade",
        occurred_at=occurred,
        symbol="XAUUSD",
        pnl=pnl,
        account_type="demo",
        test_type="forward",
        source_system="mt5_bridge",
        external_id=ticket,
    )


def test_coincidence_ratio_on_known_sets():
    from datetime import date

    days_a = {date(2026, 8, d) for d in range(1, 11)}
    days_b = {date(2026, 8, d) for d in range(1, 7)}
    assert coincidence_ratio(days_a, days_b) == 0.6
    assert coincidence_ratio(set(), set()) is None


def test_overlap_at_threshold_is_paired():
    """10 unique negative days, 6 shared → 0.6, flagged paired."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        ea_a = _profile(repo, key="london-scalper")
        ea_b = _profile(repo, key="ny-scalper")
        # Days 1–10 ago: A always negative. B negative on 1–6, positive on 7–10.
        for offset in range(1, 11):
            repo.save_evidence(
                _trade(ea_a, day_offset=offset, pnl=-10.0, ticket=f"a-{offset}")
            )
            b_pnl = -8.0 if offset <= 6 else 5.0
            repo.save_evidence(
                _trade(ea_b, day_offset=offset, pnl=b_pnl, ticket=f"b-{offset}")
            )

        result = correlate_ea_pair(
            repository=repo,
            account="demo-1",
            ea_a="london-scalper",
            ea_b="ny-scalper",
            now=AS_OF,
        )
        assert result.status == STATUS_PAIRED
        assert result.is_paired is True
        assert result.coincidence == 0.6
        assert result.coinciding_days == 6
        assert result.union_days == 10
        assert result.threshold == EA_CORRELATION_FLAG_THRESHOLD


def test_overlap_below_threshold_is_not_paired():
    """5 shared of 10 unique negative days → 0.5, not flagged."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        ea_a = _profile(repo, key="london-scalper")
        ea_b = _profile(repo, key="ny-scalper")
        for offset in range(1, 11):
            repo.save_evidence(
                _trade(ea_a, day_offset=offset, pnl=-10.0, ticket=f"a-{offset}")
            )
            b_pnl = -8.0 if offset <= 5 else 5.0
            repo.save_evidence(
                _trade(ea_b, day_offset=offset, pnl=b_pnl, ticket=f"b-{offset}")
            )

        result = correlate_ea_pair(
            repository=repo,
            account="demo-1",
            ea_a="london-scalper",
            ea_b="ny-scalper",
            now=AS_OF,
        )
        assert result.status == STATUS_NOT_PAIRED
        assert result.is_paired is False
        assert result.coincidence == 0.5


def test_insufficient_data_never_invents_a_number():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        ea_a = _profile(repo, key="london-scalper")
        _profile(repo, key="ny-scalper")
        repo.save_evidence(_trade(ea_a, day_offset=2, pnl=-4.0, ticket="a-2"))

        result = correlate_ea_pair(
            repository=repo,
            account="demo-1",
            ea_a="london-scalper",
            ea_b="ny-scalper",
            now=AS_OF,
        )
        assert result.status == STATUS_INSUFFICIENT
        assert result.coincidence is None
        assert result.is_paired is False
        assert INSUFFICIENT_LABEL in result.reason
        assert "0%" not in result.reason
        assert result.coinciding_days is None

        missing = correlate_ea_pair(
            repository=repo,
            account="demo-1",
            ea_a="london-scalper",
            ea_b="ghost-ea",
            now=AS_OF,
        )
        assert missing.status == STATUS_INSUFFICIENT
        assert missing.coincidence is None
        assert INSUFFICIENT_LABEL in missing.reason


def test_cli_paired_and_insufficient(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "knowledge.db")
        repo = KnowledgeRepository(db)
        ea_a = _profile(repo, key="london-scalper")
        ea_b = _profile(repo, key="ny-scalper")
        now = datetime.now(timezone.utc)
        for offset in range(1, 11):
            occurred = now - timedelta(days=offset)
            repo.save_evidence(
                EvidenceItem(
                    id=uuid4(),
                    ea_profile_id=ea_a.id,
                    evidence_type="trade",
                    occurred_at=occurred,
                    symbol="XAUUSD",
                    pnl=-10.0,
                    source_system="mt5_bridge",
                    external_id=f"cli-a-{offset}",
                )
            )
            repo.save_evidence(
                EvidenceItem(
                    id=uuid4(),
                    ea_profile_id=ea_b.id,
                    evidence_type="trade",
                    occurred_at=occurred,
                    symbol="XAUUSD",
                    pnl=-8.0 if offset <= 6 else 5.0,
                    source_system="mt5_bridge",
                    external_id=f"cli-b-{offset}",
                )
            )

        code = main([
            "--db", db,
            "--account", "demo-1",
            "--ea-a", "london-scalper",
            "--ea-b", "ny-scalper",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "account=demo-1" in out
        assert "london-scalper" in out
        assert "ny-scalper" in out
        assert "status=paired" in out
        assert "coincidence=0.600" in out

        code = main([
            "--db", db,
            "--account", "demo-1",
            "--ea-a", "london-scalper",
            "--ea-b", "missing-ea",
        ])
        assert code == 0
        err_out = capsys.readouterr().out
        assert INSUFFICIENT_LABEL in err_out
        assert "coincidence=omitted" in err_out
        assert "0.000" not in err_out


def test_negative_days_ignore_null_pnl():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        profile = _profile(repo, key="london-scalper")
        with_pnl = _trade(profile, day_offset=3, pnl=-2.0, ticket="p-3")
        no_pnl = _trade(profile, day_offset=4, pnl=0.0, ticket="p-4")
        no_pnl.pnl = None
        repo.save_evidence(with_pnl)
        repo.save_evidence(no_pnl)
        days = negative_pnl_days(
            repo.list_evidence_for_ea(profile.id)
        )
        assert len(days) == 1


def test_phase3_flag_remains_off_by_default():
    assert PHASE3_KNOWLEDGE_ENGINE_ENABLED is False
    env = os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower()
    assert env not in ("1", "true", "yes")

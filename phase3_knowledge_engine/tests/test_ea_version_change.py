"""EA version-change tracking: mandatory reason + quarantine clearance."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile
from phase3_knowledge_engine.domain.rules import DomainRuleViolation
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "knowledge.db"
        repo = KnowledgeRepository(db)
        yield KnowledgeEngineService(repo)


def _profile(
    *,
    ea_key: str = "london-scalper",
    version: str = "2.1.0",
    status: str = "active",
) -> EAKnowledgeProfile:
    return EAKnowledgeProfile(
        id=uuid4(),
        ea_key=ea_key,
        name=f"EA {ea_key}",
        version=version,
        purpose="Capture London open momentum on XAUUSD",
        entry_rules="Break of Asian range high with spread filter",
        exit_rules="Fixed RR 1:1.5 or session end",
        risk_rules={"max_daily_loss_pct": 2.0},
        permitted_symbols=["XAUUSD"],
        permitted_sessions=["London"],
        market_conditions={"preferred_regime": "trending"},
        status=status,  # type: ignore[arg-type]
    )


class TestRecordEaVersionChange:
    def test_rejects_empty_description(self, engine):
        profile = engine.register_ea_profile(_profile())
        with pytest.raises(DomainRuleViolation, match="description"):
            engine.record_ea_version_change(
                profile.id,
                from_version="2.1.0",
                to_version="2.2.0",
                description="",
                actor="analyst@forge",
            )
        with pytest.raises(DomainRuleViolation, match="description"):
            engine.record_ea_version_change(
                profile.id,
                from_version="2.1.0",
                to_version="2.2.0",
                description="   ",
                actor="analyst@forge",
            )
        reloaded = engine.repo.get_ea_profile(profile.id)
        assert reloaded is not None
        assert reloaded.version == "2.1.0"
        assert reloaded.status == "active"
        assert engine.repo.list_change_log_for_ea(profile.id) == []

    def test_sets_quarantine_and_persists_change_log(self, engine):
        profile = engine.register_ea_profile(_profile(status="active", version="2.1.0"))
        saved, entry = engine.record_ea_version_change(
            profile.id,
            from_version="2.1.0",
            to_version="2.2.0",
            description="Entry filter tightened after London spike losses.",
            actor="analyst@forge",
            effect_summary="Spread filter raised; expected fewer entries.",
        )
        assert saved.status == "quarantine"
        assert saved.version == "2.2.0"
        assert entry.from_version == "2.1.0"
        assert entry.to_version == "2.2.0"
        assert "Entry filter" in entry.description
        assert entry.effect_summary is not None

        reloaded = engine.repo.get_ea_profile(profile.id)
        assert reloaded is not None
        assert reloaded.status == "quarantine"
        assert reloaded.version == "2.2.0"

        log = engine.repo.list_change_log_for_ea(profile.id)
        assert len(log) == 1
        assert log[0].id == entry.id
        assert log[0].from_version == "2.1.0"
        assert log[0].to_version == "2.2.0"
        assert log[0].description == entry.description


class TestConfirmEaVersionSafe:
    def test_fails_when_not_quarantine(self, engine):
        profile = engine.register_ea_profile(_profile(status="active"))
        with pytest.raises(DomainRuleViolation, match="quarantine"):
            engine.confirm_ea_version_safe(
                profile.id,
                actor="lead@forge",
                justification="Looks fine after paper trading.",
            )
        reloaded = engine.repo.get_ea_profile(profile.id)
        assert reloaded is not None
        assert reloaded.status == "active"

    def test_succeeds_from_quarantine_to_active(self, engine):
        profile = engine.register_ea_profile(_profile(status="active", version="2.1.0"))
        engine.record_ea_version_change(
            profile.id,
            from_version="2.1.0",
            to_version="2.2.0",
            description="Risk rules updated for Asian session.",
            actor="analyst@forge",
        )
        cleared = engine.confirm_ea_version_safe(
            profile.id,
            actor="lead@forge",
            justification="Forward demo week clean; human clearance.",
        )
        assert cleared.status == "active"
        assert cleared.version == "2.2.0"
        reloaded = engine.repo.get_ea_profile(profile.id)
        assert reloaded is not None
        assert reloaded.status == "active"


class TestListEaProfiles:
    def test_list_all_and_filter_by_status_including_quarantine(self, engine):
        a = engine.register_ea_profile(
            _profile(ea_key="ea-active", status="active")
        )
        engine.register_ea_profile(
            _profile(ea_key="ea-testing", status="testing")
        )
        engine.register_ea_profile(
            _profile(ea_key="ea-restricted", status="restricted")
        )
        engine.record_ea_version_change(
            a.id,
            from_version="2.1.0",
            to_version="2.2.0",
            description="Quarantine candidate after version bump.",
            actor="analyst@forge",
        )

        all_profiles = engine.repo.list_ea_profiles()
        assert {p.ea_key for p in all_profiles} == {
            "ea-active",
            "ea-testing",
            "ea-restricted",
        }

        quarantine = engine.repo.list_ea_profiles(status="quarantine")
        assert len(quarantine) == 1
        assert quarantine[0].ea_key == "ea-active"
        assert quarantine[0].status == "quarantine"
        assert quarantine[0].version == "2.2.0"

        testing = engine.repo.list_ea_profiles(status="testing")
        assert len(testing) == 1
        assert testing[0].ea_key == "ea-testing"

        active = engine.repo.list_ea_profiles(status="active")
        assert active == []

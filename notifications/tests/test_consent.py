"""Consent: no default-on preference, no bulk enable, inactive unless explicit."""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

from notifications.application.services import PreferenceService
from notifications.domain.entities import NotificationPreference
from notifications.infrastructure.repositories import NotificationPreferenceRepository, new_id


def test_entity_active_defaults_false():
    pref = NotificationPreference(
        id=new_id(),
        user_id="alice",
        account_id="MT5-1111",
        alert_type="risk_drawdown",
        priority="normal",
        frequency="immediate",
        channel="telegram",
    )
    assert pref.active is False


def test_create_without_active_flag_stores_inactive():
    with tempfile.TemporaryDirectory() as tmp:
        svc = PreferenceService(
            NotificationPreferenceRepository(Path(tmp) / "notifications.db")
        )
        pref = svc.create(
            actor="alice",
            user_id="alice",
            account_id="MT5-1111",
            alert_type="risk_drawdown",
            priority="high",
            frequency="immediate",
            channel="telegram",
        )
        assert pref.active is False
        loaded = svc.list_for_account("alice", "MT5-1111")
        assert loaded[0].active is False


def test_active_only_when_explicitly_requested():
    with tempfile.TemporaryDirectory() as tmp:
        svc = PreferenceService(
            NotificationPreferenceRepository(Path(tmp) / "notifications.db")
        )
        pref = svc.create(
            actor="alice",
            user_id="alice",
            account_id="MT5-1111",
            alert_type="new_knowledge",
            priority="normal",
            frequency="digest",
            channel="email",
            active=True,
        )
        assert pref.active is True


def test_empty_database_has_no_preferences():
    with tempfile.TemporaryDirectory() as tmp:
        svc = PreferenceService(
            NotificationPreferenceRepository(Path(tmp) / "notifications.db")
        )
        assert svc.list_for_account("alice", "MT5-1111") == []


def test_service_has_no_bulk_enable_helper():
    names = {name for name in dir(PreferenceService) if not name.startswith("_")}
    forbidden = {
        "enable_all",
        "bulk_enable",
        "activate_all",
        "enable_defaults",
        "default_on",
    }
    assert names.isdisjoint(forbidden)
    source = inspect.getsource(PreferenceService)
    lowered = source.lower()
    assert "bulk" not in lowered
    assert "enable_all" not in lowered

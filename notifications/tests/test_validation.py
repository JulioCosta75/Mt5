"""Unknown or malformed preference fields are rejected with a clear error."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from notifications.application.services import PreferenceService
from notifications.domain.rules import PreferenceValidationError
from notifications.infrastructure.repositories import NotificationPreferenceRepository


def _svc(tmp: str) -> PreferenceService:
    return PreferenceService(NotificationPreferenceRepository(Path(tmp) / "notifications.db"))


def _create(svc: PreferenceService, **overrides):
    payload = dict(
        actor="alice",
        user_id="alice",
        account_id="MT5-1111",
        alert_type="risk_drawdown",
        priority="normal",
        frequency="immediate",
        channel="telegram",
    )
    payload.update(overrides)
    return svc.create(**payload)


def test_unknown_alert_type_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(PreferenceValidationError, match="unknown alert_type"):
            _create(_svc(tmp), alert_type="price_prediction")


def test_invalid_frequency_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(PreferenceValidationError, match="invalid frequency"):
            _create(_svc(tmp), frequency="hourly")


def test_malformed_quiet_hours_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        svc = _svc(tmp)
        with pytest.raises(PreferenceValidationError, match="malformed quiet_hours_start"):
            _create(svc, quiet_hours_start="25:00", quiet_hours_end="07:00")
        with pytest.raises(PreferenceValidationError, match="malformed quiet_hours_end"):
            _create(svc, quiet_hours_start="22:00", quiet_hours_end="9:00")
        with pytest.raises(PreferenceValidationError, match="both be set or both omitted"):
            _create(svc, quiet_hours_start="22:00", quiet_hours_end=None)


def test_malformed_account_id_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(PreferenceValidationError, match="MT5-\\{login\\}"):
            _create(_svc(tmp), account_id="1111")
        with pytest.raises(PreferenceValidationError, match="MT5-\\{login\\}"):
            _create(_svc(tmp), account_id="ACC-001")


def test_valid_quiet_hours_accepted():
    with tempfile.TemporaryDirectory() as tmp:
        pref = _create(
            _svc(tmp), quiet_hours_start="22:00", quiet_hours_end="07:00"
        )
        assert pref.quiet_hours_start == "22:00"
        assert pref.quiet_hours_end == "07:00"

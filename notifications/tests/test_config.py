"""Flag defaults for the isolated notifications module."""

from __future__ import annotations

from notifications.config import ATLAS_NOTIFICATIONS_ENABLED


def test_feature_flag_off_by_default():
    assert ATLAS_NOTIFICATIONS_ENABLED is False

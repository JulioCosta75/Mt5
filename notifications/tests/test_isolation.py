"""Two users × two accounts: listing never crosses tenant boundaries."""

from __future__ import annotations

import tempfile
from pathlib import Path

from notifications.application.services import PreferenceService
from notifications.infrastructure.repositories import NotificationPreferenceRepository


def _svc(tmp: str) -> PreferenceService:
    return PreferenceService(NotificationPreferenceRepository(Path(tmp) / "notifications.db"))


def test_list_never_returns_another_user_or_account():
    with tempfile.TemporaryDirectory() as tmp:
        svc = _svc(tmp)
        seeds = (
            ("alice", "MT5-1111", "risk_drawdown", "alice-1111"),
            ("alice", "MT5-2222", "account_change", "alice-2222"),
            ("bob", "MT5-1111", "ea_status", "bob-1111"),
            ("bob", "MT5-3333", "technical_failure", "bob-3333"),
        )
        created = {}
        for user, account, alert_type, tag in seeds:
            pref = svc.create(
                actor=user,
                user_id=user,
                account_id=account,
                alert_type=alert_type,
                priority="normal",
                frequency="immediate",
                channel="telegram",
            )
            created[tag] = pref

        alice_1111 = svc.list_for_account("alice", "MT5-1111")
        assert [p.id for p in alice_1111] == [created["alice-1111"].id]
        assert all(p.user_id == "alice" and p.account_id == "MT5-1111" for p in alice_1111)
        blob = str([p.alert_type for p in alice_1111])
        assert "account_change" not in blob
        assert "ea_status" not in blob
        assert "technical_failure" not in blob

        alice_2222 = svc.list_for_account("alice", "MT5-2222")
        assert [p.id for p in alice_2222] == [created["alice-2222"].id]
        assert alice_2222[0].user_id == "alice"

        bob_1111 = svc.list_for_account("bob", "MT5-1111")
        assert [p.id for p in bob_1111] == [created["bob-1111"].id]
        assert bob_1111[0].user_id == "bob"
        assert created["alice-1111"].id not in [p.id for p in bob_1111]

        bob_3333 = svc.list_for_account("bob", "MT5-3333")
        assert [p.id for p in bob_3333] == [created["bob-3333"].id]

        empty = svc.list_for_account("alice", "MT5-3333")
        assert empty == []

        stolen = svc.repo.get_preference(
            "bob", "MT5-1111", created["alice-1111"].id
        )
        assert stolen is None

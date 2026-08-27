"""Unit tests — alerts_since_previous report field (factual event window)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from atlas_alerts import (
    RULE_DRAWDOWN,
    alerts_events_since,
    load_alerts_since_previous,
)
from atlas_reports import build_account_report
from atlas_store import AtlasAlertStore


def _run(coro):
    return asyncio.run(coro)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


class TestAlertsEventsSince:
    def test_no_previous_report_yields_empty(self):
        alerts = [{
            "account_id": "MT5-1",
            "rule_key": RULE_DRAWDOWN,
            "severity": "WARNING",
            "message": "dd",
            "created_at": _iso(datetime.now(timezone.utc)),
            "acknowledged_at": None,
            "resolved_at": None,
        }]
        assert alerts_events_since(alerts, since_iso=None) == []
        assert alerts_events_since(alerts, since_iso="") == []

    def test_created_in_window(self):
        t0 = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        created = t0 + timedelta(minutes=30)
        alerts = [{
            "account_id": "MT5-1",
            "rule_key": RULE_DRAWDOWN,
            "severity": "WARNING",
            "message": "drawdown breach",
            "created_at": _iso(created),
            "acknowledged_at": None,
            "resolved_at": None,
        }]
        events = alerts_events_since(alerts, since_iso=_iso(t0), account_id="MT5-1")
        assert len(events) == 1
        assert events[0]["state"] == "active"
        assert events[0]["rule_key"] == RULE_DRAWDOWN
        assert events[0]["severity"] == "WARNING"
        assert events[0]["message"] == "drawdown breach"
        assert events[0]["event_at"] == _iso(created)

    def test_resolved_in_window(self):
        t0 = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        # Created before previous report; resolved after → only resolve event.
        alerts = [{
            "account_id": "MT5-1",
            "rule_key": RULE_DRAWDOWN,
            "severity": "WARNING",
            "message": "drawdown breach",
            "created_at": _iso(t0 - timedelta(hours=2)),
            "acknowledged_at": None,
            "resolved_at": _iso(t0 + timedelta(minutes=10)),
        }]
        events = alerts_events_since(alerts, since_iso=_iso(t0))
        assert len(events) == 1
        assert events[0]["state"] == "resolved"
        assert events[0]["event_at"] == alerts[0]["resolved_at"]

    def test_build_report_empty_without_previous(self):
        acc = {
            "id": "MT5-1",
            "login": 1,
            "status": "LIVE",
            "equity": 1000,
            "current_drawdown": 0.0,
            "risk_limits": {},
        }
        report = build_account_report(
            acc,
            source="manual",
            bridge_ok=True,
            previous_report=None,
            alerts_since_previous=[{
                "rule_key": RULE_DRAWDOWN,
                "severity": "WARNING",
                "message": "should be dropped",
                "state": "active",
                "event_at": _iso(datetime.now(timezone.utc)),
            }],
        )
        assert report["alerts_since_previous"] == []

    def test_load_via_store_created_and_resolved(self, tmp_path: Path):
        store = AtlasAlertStore(sqlite_path=tmp_path / "atlas.db")
        t0 = datetime.now(timezone.utc) - timedelta(hours=1)
        since = _iso(t0)

        created = _run(
            store.create({
                "account_id": "MT5-1",
                "rule_key": RULE_DRAWDOWN,
                "severity": "WARNING",
                "message": "new breach",
            })
        )
        # Older alert created before window, resolved after.
        old = _run(
            store.create({
                "account_id": "MT5-1",
                "rule_key": "account_error",
                "severity": "CRITICAL",
                "message": "was error",
            })
        )
        # Backdate created_at of "old" before since (direct persist).
        old["created_at"] = _iso(t0 - timedelta(hours=2))
        old["updated_at"] = old["created_at"]
        _run(store._persist(old))
        resolved = _run(store.resolve(old["id"]))

        events = _run(
            load_alerts_since_previous(
                store, account_id="MT5-1", since_iso=since
            )
        )
        states = {e["state"] for e in events}
        assert "active" in states  # created in window
        assert "resolved" in states  # resolved in window
        created_ev = next(e for e in events if e["state"] == "active")
        assert created_ev["rule_key"] == RULE_DRAWDOWN
        assert created_ev["event_at"] == created["created_at"]
        resolved_ev = next(e for e in events if e["state"] == "resolved")
        assert resolved_ev["rule_key"] == "account_error"
        assert resolved_ev["event_at"] == resolved["resolved_at"]

        # No previous → empty even if store has rows.
        assert _run(
            load_alerts_since_previous(
                store, account_id="MT5-1", since_iso=None
            )
        ) == []

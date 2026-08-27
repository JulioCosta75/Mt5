"""Unit tests — Phase 2 part 4: fixed-rule alert engine.

Covers evaluation, reconcile (no duplicates while open), state transitions,
bridge-unreachable rule, and SQLite migration safety.
"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from atlas_alerts import (
    RULE_ACCOUNT_ERROR,
    RULE_BRIDGE_DOWN,
    RULE_DRAWDOWN,
    RULE_OPEN_POSITIONS,
    RULE_VOLUME,
    evaluate_account_conditions,
    evaluate_and_persist_account_alerts,
    reconcile_alerts,
    to_api_alert,
)
from atlas_store import AtlasAlertStore, AtlasReportStore
from mt5_cache_sqlite import MT5CacheSQLite


def _run(coro):
    return asyncio.run(coro)


def _acc(
    account_id: str = "MT5-100",
    *,
    login: int = 100,
    status: str = "LIVE",
    current_drawdown: float = 0.0,
    open_positions: int = 0,
    max_daily_loss_pct: float = 5.0,
    max_open_positions: int = 20,
    max_position_size_lots: float = 1.0,
    stale: bool = False,
) -> dict:
    return {
        "id": account_id,
        "login": login,
        "status": status,
        "current_drawdown": current_drawdown,
        "open_positions": open_positions,
        "stale": stale,
        "risk_limits": {
            "max_daily_loss_pct": max_daily_loss_pct,
            "max_open_positions": max_open_positions,
            "max_position_size_lots": max_position_size_lots,
        },
    }


class TestEvaluateConditions:
    def test_bridge_down_fires_critical(self):
        firing = evaluate_account_conditions(_acc(), bridge_ok=False)
        keys = {c["rule_key"] for c in firing}
        assert RULE_BRIDGE_DOWN in keys
        bridge = next(c for c in firing if c["rule_key"] == RULE_BRIDGE_DOWN)
        assert bridge["severity"] == "CRITICAL"
        assert "cannot be OK" in bridge["message"]

    def test_bridge_ok_no_bridge_alert(self):
        firing = evaluate_account_conditions(_acc(), bridge_ok=True)
        assert RULE_BRIDGE_DOWN not in {c["rule_key"] for c in firing}

    def test_account_error_critical(self):
        firing = evaluate_account_conditions(
            _acc(status="ERROR"), bridge_ok=True
        )
        assert any(c["rule_key"] == RULE_ACCOUNT_ERROR for c in firing)

    def test_drawdown_at_limit(self):
        firing = evaluate_account_conditions(
            _acc(current_drawdown=-5.0, max_daily_loss_pct=5.0),
            bridge_ok=True,
        )
        assert any(c["rule_key"] == RULE_DRAWDOWN for c in firing)

    def test_drawdown_below_limit_silent(self):
        firing = evaluate_account_conditions(
            _acc(current_drawdown=-4.9, max_daily_loss_pct=5.0),
            bridge_ok=True,
        )
        assert RULE_DRAWDOWN not in {c["rule_key"] for c in firing}

    def test_open_positions_limit(self):
        positions = [{"ticket": i, "volume": 0.1} for i in range(20)]
        firing = evaluate_account_conditions(
            _acc(max_open_positions=20),
            bridge_ok=True,
            open_positions=positions,
        )
        assert any(c["rule_key"] == RULE_OPEN_POSITIONS for c in firing)

    def test_volume_limit(self):
        firing = evaluate_account_conditions(
            _acc(max_position_size_lots=1.0),
            bridge_ok=True,
            open_positions=[{"ticket": 1, "volume": 1.5}],
        )
        assert any(c["rule_key"] == RULE_VOLUME for c in firing)


class TestReconcile:
    def test_never_recreate_while_active(self):
        existing = [{
            "id": "A1",
            "account_id": "MT5-100",
            "rule_key": RULE_DRAWDOWN,
            "state": "active",
        }]
        firing = [{
            "rule_key": RULE_DRAWDOWN,
            "severity": "WARNING",
            "account_id": "MT5-100",
            "message": "still over limit",
        }]
        plan = reconcile_alerts(
            existing_open=existing, firing=firing, account_id="MT5-100"
        )
        assert plan["create"] == []
        assert plan["resolve"] == []
        assert len(plan["keep"]) == 1

    def test_never_recreate_while_acknowledged(self):
        existing = [{
            "id": "A1",
            "account_id": "MT5-100",
            "rule_key": RULE_BRIDGE_DOWN,
            "state": "acknowledged",
        }]
        firing = [{
            "rule_key": RULE_BRIDGE_DOWN,
            "severity": "CRITICAL",
            "account_id": "MT5-100",
            "message": "still down",
        }]
        plan = reconcile_alerts(
            existing_open=existing, firing=firing, account_id="MT5-100"
        )
        assert plan["create"] == []
        assert plan["keep"][0]["id"] == "A1"

    def test_resolve_when_condition_clears(self):
        existing = [{
            "id": "A1",
            "account_id": "MT5-100",
            "rule_key": RULE_DRAWDOWN,
            "state": "active",
        }]
        plan = reconcile_alerts(
            existing_open=existing, firing=[], account_id="MT5-100"
        )
        assert len(plan["resolve"]) == 1
        assert plan["create"] == []

    def test_create_when_new_condition(self):
        plan = reconcile_alerts(
            existing_open=[],
            firing=[{
                "rule_key": RULE_ACCOUNT_ERROR,
                "severity": "CRITICAL",
                "account_id": "MT5-100",
                "message": "ERROR",
            }],
            account_id="MT5-100",
        )
        assert len(plan["create"]) == 1


class TestAlertStoreLifecycle:
    def test_active_ack_resolved_and_no_duplicate(self, tmp_path: Path):
        store = AtlasAlertStore(sqlite_path=tmp_path / "atlas.db")
        acc = _acc(current_drawdown=-6.0)

        r1 = _run(
            evaluate_and_persist_account_alerts(
                store, acc, bridge_ok=True, open_positions=[]
            )
        )
        assert len(r1["created"]) == 1
        alert_id = r1["created"][0]["id"]
        assert r1["created"][0]["state"] == "active"
        assert r1["created"][0]["rule_key"] == RULE_DRAWDOWN

        # Second snapshot while still over limit — must NOT recreate.
        r2 = _run(
            evaluate_and_persist_account_alerts(
                store, acc, bridge_ok=True, open_positions=[]
            )
        )
        assert r2["created"] == []
        assert len(r2["kept"]) == 1
        assert r2["kept"][0]["id"] == alert_id
        open_rows = _run(store.list_open(account_id="MT5-100"))
        assert len(open_rows) == 1

        # Human acknowledges.
        acked = _run(store.acknowledge(alert_id, True))
        assert acked is not None
        assert acked["state"] == "acknowledged"
        api = to_api_alert(acked)
        assert api["acknowledged"] is True

        # Still over limit after ack — still no recreate.
        r3 = _run(
            evaluate_and_persist_account_alerts(
                store, acc, bridge_ok=True, open_positions=[]
            )
        )
        assert r3["created"] == []
        assert r3["kept"][0]["state"] == "acknowledged"

        # Condition clears → resolved.
        cleared = _acc(current_drawdown=-1.0)
        r4 = _run(
            evaluate_and_persist_account_alerts(
                store, cleared, bridge_ok=True, open_positions=[]
            )
        )
        assert len(r4["resolved"]) == 1
        assert r4["resolved"][0]["state"] == "resolved"
        assert r4["resolved"][0]["resolved_at"]
        assert _run(store.list_open(account_id="MT5-100")) == []

        # Same condition returns later → NEW alert (previous was resolved).
        r5 = _run(
            evaluate_and_persist_account_alerts(
                store, acc, bridge_ok=True, open_positions=[]
            )
        )
        assert len(r5["created"]) == 1
        assert r5["created"][0]["id"] != alert_id

    def test_limit_raise_resolves_on_same_evaluation(self, tmp_path: Path):
        """Engine sees the same risk_limits as the report on one snapshot.

        Documents that a one-cycle UI lag is not caused by stale overrides
        inside evaluate_and_persist when the account dict already has the
        updated limit (live path loads get_overrides before both report and
        alerts on the same capture).
        """
        store = AtlasAlertStore(sqlite_path=tmp_path / "atlas.db")
        positions = [{"ticket": i, "volume": 0.1} for i in range(5)]
        breached = _acc(max_open_positions=5, open_positions=5)
        _run(
            evaluate_and_persist_account_alerts(
                store, breached, bridge_ok=True, open_positions=positions
            )
        )
        assert len(_run(store.list_open(account_id="MT5-100"))) == 1

        # Same snapshot moment: limit raised to 20 with only 5 positions.
        cleared = _acc(max_open_positions=20, open_positions=5)
        result = _run(
            evaluate_and_persist_account_alerts(
                store, cleared, bridge_ok=True, open_positions=positions
            )
        )
        assert len(result["resolved"]) == 1
        assert _run(store.list_open(account_id="MT5-100")) == []

    def test_bridge_down_persists_critical_alert(self, tmp_path: Path):
        store = AtlasAlertStore(sqlite_path=tmp_path / "atlas.db")
        result = _run(
            evaluate_and_persist_account_alerts(
                store, _acc(stale=True), bridge_ok=False, open_positions=[]
            )
        )
        assert any(a["rule_key"] == RULE_BRIDGE_DOWN for a in result["created"])
        bridge = next(a for a in result["created"] if a["rule_key"] == RULE_BRIDGE_DOWN)
        assert bridge["severity"] == "CRITICAL"

    def test_memory_backend_ack_404_style(self):
        store = AtlasAlertStore()
        assert _run(store.acknowledge("missing")) is None
        assert store.backend == "memory"


class TestMigrationWithAlerts:
    def test_alert_store_does_not_destroy_cache_or_reports(self, tmp_path: Path):
        db = tmp_path / "atlas.db"
        cache = MT5CacheSQLite(str(db))
        _run(cache.put("account:7", {"login": 7, "equity": 1.0}))

        reports = AtlasReportStore(sqlite_path=db)
        _run(
            reports.add(
                {
                    "account_id": "MT5-7",
                    "status": "OK",
                    "source": "auto",
                    "message": "ok",
                }
            )
        )

        alerts = AtlasAlertStore(sqlite_path=db)
        _run(
            alerts.create(
                {
                    "account_id": "MT5-7",
                    "rule_key": RULE_BRIDGE_DOWN,
                    "severity": "CRITICAL",
                    "message": "bridge down",
                }
            )
        )

        with sqlite3.connect(str(db)) as cx:
            tables = {
                r[0]
                for r in cx.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "mt5_cache" in tables
        assert "atlas_reports" in tables
        assert "atlas_alerts" in tables
        assert _run(cache.get("account:7"))["payload"]["login"] == 7
        assert _run(reports.count()) == 1
        assert len(_run(alerts.list_open())) == 1

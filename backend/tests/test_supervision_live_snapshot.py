"""Unit tests for Phase 2 live supervision snapshot severity and stale-cache messaging.

These tests exercise `_supervision_snapshot_from_accounts` and MT5-mode route
isolation without writing to .env or touching protected runtime files.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _reload_server(*, mt5: bool):
    """Import/reload server with controlled bridge env (does not write .env)."""
    if mt5:
        os.environ["MT5_BRIDGE_URL"] = "http://127.0.0.1:9"
        os.environ["MT5_BRIDGE_TOKEN"] = "test-token"
    else:
        os.environ.pop("MT5_BRIDGE_URL", None)
        os.environ.pop("MT5_BRIDGE_URLS", None)
        os.environ.pop("MT5_BRIDGE_TOKEN", None)
        os.environ.pop("MT5_BRIDGE_TOKENS", None)
    os.environ.setdefault("ATLAS_STORE", "sqlite")
    # Avoid clobbering the developer's real atlas.db during import-time init.
    os.environ["ATLAS_SQLITE_PATH"] = str(BACKEND_DIR / "data" / "_pytest_supervision.db")
    for name in list(sys.modules):
        if name == "server" or name.startswith("server."):
            del sys.modules[name]
    return importlib.import_module("server")


def _live_account(**overrides):
    base = {
        "id": "MT5-62127915",
        "login": 62127915,
        "equity": 1013.37,
        "balance": 1010.67,
        "daily_pnl": 2.7,
        "open_positions": 2,
        "current_drawdown": -0.5,
        "status": "LIVE",
        "risk_limits": {"max_daily_loss_pct": 5.0},
        "source": "mt5",
    }
    base.update(overrides)
    return base


class TestSupervisionSnapshotSeverity:
    @pytest.fixture(scope="class")
    def snap_fn(self):
        mod = _reload_server(mt5=True)
        return mod._supervision_snapshot_from_accounts

    def test_healthy_bridge_live_accounts_ok(self, snap_fn):
        d = snap_fn([_live_account()], bridge_ok=True, alerts=[])
        assert d["services"]["bridge_ok"] is True
        assert d["status"] == "OK"
        assert d["accounts"]["total"] == 1
        assert d["accounts"]["live"] == 1
        assert "All Forge Factory Lab core services are online and healthy." in d["message"]
        assert "cache" not in d["message"].lower()
        assert "unavailable" not in d["message"].lower()

    def test_bridge_down_with_stale_cache_warning(self, snap_fn):
        cached = _live_account(stale=True)
        d = snap_fn([cached], bridge_ok=False, alerts=[])
        assert d["services"]["bridge_ok"] is False
        assert d["status"] == "WARNING"
        assert d["accounts"]["total"] == 1
        assert d["kpis"]["total_equity"] == pytest.approx(1013.37)
        msg = d["message"].lower()
        assert "mt5 bridge is unavailable" in msg
        assert "cache" in msg
        assert "outdated" in msg or "desatualiz" in msg
        assert "all forge factory lab core services are online and healthy" not in msg

    def test_bridge_down_without_cache_warning(self, snap_fn):
        d = snap_fn([], bridge_ok=False, alerts=[])
        assert d["services"]["bridge_ok"] is False
        assert d["status"] == "WARNING"
        assert d["accounts"]["total"] == 0
        msg = d["message"].lower()
        assert "mt5 bridge is unavailable" in msg
        assert "no cached account data" in msg
        assert "all forge factory lab core services are online and healthy" not in msg

    def test_alert_priority_with_bridge_down(self, snap_fn):
        critical_acc = _live_account(status="ERROR", stale=True, equity=500.0)
        d = snap_fn([critical_acc], bridge_ok=False, alerts=[])
        assert d["services"]["bridge_ok"] is False
        assert d["status"] == "ALERT"
        assert d["accounts"]["error"] == 1
        msg = d["message"].lower()
        assert msg.startswith("alert:")
        assert "mt5 bridge is unavailable" in msg
        assert "cache" in msg
        assert "outdated" in msg or "desatualiz" in msg
        assert "all forge factory lab core services are online and healthy" not in msg

    def test_real_path_never_uses_mock_alerts(self, snap_fn):
        # alerts=[] is the live-path contract; mock ALERTS must not leak in.
        d = snap_fn([_live_account()], bridge_ok=True, alerts=[])
        assert d["alerts"]["active"] == 0
        assert d["alerts"]["critical"] == 0
        assert d["alerts"]["warning"] == 0


class TestMt5ModeIsolation:
    def test_mt5_mode_does_not_mount_mock_api_router(self):
        mod = _reload_server(mt5=True)
        assert mod.MT5_MODE is True
        paths = {getattr(route, "path", "") for route in mod.app.routes}
        # Mock-only route from api_router — must not be mounted in MT5 mode.
        assert "/api/sim/tick" not in paths
        # Live supervision remains available on the app.
        assert "/api/supervision/snapshot" in paths
        # Live accounts route comes from routes_mt5, not mock ACC-* catalogue.
        assert "/api/accounts" in paths

        snap = asyncio.run(mod._live_supervision_snapshot())
        assert snap["mode"] == "mt5"
        assert snap["services"]["bridge_ok"] is False
        assert snap["status"] == "WARNING"
        assert snap["accounts"]["total"] == 0
        assert "all forge factory lab core services are online and healthy." not in snap["message"].lower()

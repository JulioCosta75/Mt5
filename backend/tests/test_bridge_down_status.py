"""`_connection_status` reports bridge_down when the last bridge check failed.

In-process only: no preview URL, no MT5, no bridge.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import server  # noqa: E402

CFG = {"configured": True, "terminal_path": r"C:\MT5\terminal64.exe"}


@pytest.mark.parametrize(
    ("mt5_mode", "last_ok", "expected"),
    [
        (True, False, "bridge_down"),
        (True, True, "connected"),
        (True, None, "connected"),  # not measured yet: unchanged behaviour
        (False, False, "pending_restart"),  # mock mode ignores the bridge flag
    ],
)
def test_state_follows_last_bridge_check(monkeypatch, mt5_mode, last_ok, expected):
    monkeypatch.setattr(server, "MT5_MODE", mt5_mode)
    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", last_ok)
    assert server._connection_status(CFG)["state"] == expected


def test_live_accounts_records_bridge_result(monkeypatch):
    import asyncio

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", None)
    monkeypatch.setattr(server, "_cache", None)
    import mt5_client

    monkeypatch.setattr(mt5_client, "clients", lambda: [])
    accounts, ok = asyncio.run(server._mt5_live_accounts())
    assert ok is False
    assert server._LAST_BRIDGE_OK is False


def test_status_follows_failure_then_recovery(monkeypatch):
    """The config endpoint reflects each new bridge measurement (down, then back up)."""
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server, "MT5_MODE", True)
    monkeypatch.setattr(server._mt5cfg, "load", lambda: dict(CFG))
    client = TestClient(server.app)

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", False)
    assert client.get("/api/mt5/config").json()["status"]["state"] == "bridge_down"

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", True)
    assert client.get("/api/mt5/config").json()["status"]["state"] == "connected"

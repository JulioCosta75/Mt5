"""`_connection_status` reports bridge_down when the last bridge check failed.

`/health` reachability and terminal login stay separate from `_LAST_BRIDGE_OK`
(the account-fetch result). A bad token must not read as connected.

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
    monkeypatch.setattr(server, "_LAST_BRIDGE_REACHABLE", None)
    monkeypatch.setattr(server, "_LAST_TERMINAL_OK", None)
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
    """The config endpoint reflects each new account-fetch measurement (down, then back up)."""
    import mt5_client
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server, "MT5_MODE", True)
    monkeypatch.setattr(server._mt5cfg, "load", lambda: dict(CFG))
    monkeypatch.setattr(mt5_client, "clients", lambda: [])
    monkeypatch.setattr(server, "_LAST_BRIDGE_REACHABLE", None)
    monkeypatch.setattr(server, "_LAST_TERMINAL_OK", None)
    client = TestClient(server.app)

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", False)
    assert client.get("/api/mt5/config").json()["status"]["state"] == "bridge_down"

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", True)
    assert client.get("/api/mt5/config").json()["status"]["state"] == "connected"


@pytest.mark.parametrize(
    ("last_ok", "reachable", "terminal_ok", "expected"),
    [
        (False, True, False, "mt5_offline"),  # bridge up, terminal closed (test 2026-11-14)
        (True, True, False, "mt5_offline"),
        (False, False, None, "bridge_down"),
        (False, None, None, "bridge_down"),   # reachability not measured: account fetch failed
        (True, True, True, "connected"),
        (False, True, True, "bridge_down"),   # /health says logged in; account fetch failed (bad token)
        (None, True, True, "connected"),      # /health ok; account fetch not measured yet
    ],
)
def test_terminal_closed_is_not_bridge_down(monkeypatch, last_ok, reachable, terminal_ok, expected):
    monkeypatch.setattr(server, "MT5_MODE", True)
    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", last_ok)
    monkeypatch.setattr(server, "_LAST_BRIDGE_REACHABLE", reachable)
    monkeypatch.setattr(server, "_LAST_TERMINAL_OK", terminal_ok)
    assert server._connection_status(CFG)["state"] == expected


def test_probe_reads_bridge_health(monkeypatch):
    import asyncio
    import mt5_client

    class Bridge:
        def __init__(self, health=None, fail=False):
            self._h, self._fail = health, fail

        async def health(self):
            if self._fail:
                raise RuntimeError("connection refused")
            return self._h

    monkeypatch.setattr(server, "MT5_MODE", True)
    # Account fetch already failed. /health must not rewrite that result.
    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", False)
    monkeypatch.setattr(server, "_LAST_BRIDGE_REACHABLE", None)
    monkeypatch.setattr(server, "_LAST_TERMINAL_OK", None)

    monkeypatch.setattr(mt5_client, "clients", lambda: [Bridge({"terminal_connected": False, "account_logged_in": False})])
    asyncio.run(server._probe_bridge_health())
    assert server._LAST_BRIDGE_OK is False
    assert server._LAST_BRIDGE_REACHABLE is True
    assert server._LAST_TERMINAL_OK is False
    assert server._connection_status(CFG)["state"] == "mt5_offline"

    # Terminal logged in on the unauthenticated /health route. A bad token
    # still failed the account fetch, so the card stays bridge_down.
    monkeypatch.setattr(mt5_client, "clients", lambda: [Bridge({"terminal_connected": True, "account_logged_in": True})])
    asyncio.run(server._probe_bridge_health())
    assert server._LAST_BRIDGE_OK is False
    assert server._LAST_TERMINAL_OK is True
    assert server._connection_status(CFG)["state"] == "bridge_down"

    monkeypatch.setattr(mt5_client, "clients", lambda: [Bridge(fail=True)])
    asyncio.run(server._probe_bridge_health())
    assert server._LAST_BRIDGE_OK is False
    assert server._LAST_BRIDGE_REACHABLE is False
    assert server._connection_status(CFG)["state"] == "bridge_down"

    monkeypatch.setattr(server, "_LAST_BRIDGE_OK", True)
    monkeypatch.setattr(mt5_client, "clients", lambda: [Bridge({"terminal_connected": True, "account_logged_in": True})])
    asyncio.run(server._probe_bridge_health())
    assert server._LAST_BRIDGE_OK is True
    assert server._connection_status(CFG)["state"] == "connected"

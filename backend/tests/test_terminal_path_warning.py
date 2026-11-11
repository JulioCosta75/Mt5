"""`terminal_path_missing` warning in the MT5 connection status.

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


@pytest.mark.parametrize(
    ("cfg", "expected"),
    [
        ({"configured": True, "terminal_path": ""}, ["terminal_path_missing"]),
        ({"configured": True}, ["terminal_path_missing"]),
        ({"configured": True, "terminal_path": None}, ["terminal_path_missing"]),
        ({"configured": True, "terminal_path": "   "}, ["terminal_path_missing"]),
        (
            {"configured": True, "terminal_path": r"C:\Program Files\MetaTrader 5\terminal64.exe"},
            [],
        ),
        ({"configured": False, "terminal_path": ""}, []),
        ({}, []),
    ],
)
def test_connection_status_warnings(cfg, expected):
    status = server._connection_status(cfg)
    assert status["warnings"] == expected


def test_existing_fields_are_unchanged():
    status = server._connection_status({"configured": True, "terminal_path": ""})
    for key in (
        "mode",
        "configured",
        "state",
        "platform",
        "server",
        "login",
        "bridge_port",
        "updated_at",
    ):
        assert key in status
    assert status["configured"] is True


def test_get_config_endpoint_exposes_warning(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(
        server._mt5cfg, "load", lambda: {"configured": True, "terminal_path": ""}
    )
    monkeypatch.setattr(server._mt5cfg, "masked", lambda cfg: {})
    r = TestClient(server.app).get("/api/mt5/config")
    assert r.status_code == 200, r.text
    assert r.json()["status"]["warnings"] == ["terminal_path_missing"]

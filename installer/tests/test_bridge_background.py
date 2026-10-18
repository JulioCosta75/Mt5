"""Bridge HTTP stays up while MT5 initialize runs. No real terminal."""
from __future__ import annotations

import importlib
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "mt5-bridge"

_BRIDGE_MODULES = (
    "config",
    "bridge_server",
    "mt5_service",
    "storage",
    "snapshot_recorder",
    "equity_reconstructor",
)


@pytest.fixture(autouse=True)
def _drop_bridge_modules():
    yield
    for name in _BRIDGE_MODULES:
        sys.modules.pop(name, None)
    while str(BRIDGE) in sys.path:
        sys.path.remove(str(BRIDGE))


def _load_bridge(monkeypatch, tmp_path: Path, **env: str):
    for key in (
        "MT5_LOGIN",
        "MT5_PASSWORD",
        "MT5_SERVER",
        "MT5_TERMINAL_PATH",
        "BRIDGE_TOKEN",
        "SQLITE_PATH",
        "SNAPSHOT_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "bridge.db"))
    monkeypatch.setenv("SNAPSHOT_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("BRIDGE_TOKEN", "test-token")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.path.insert(0, str(BRIDGE))
    for name in _BRIDGE_MODULES:
        sys.modules.pop(name, None)
    return importlib.import_module("bridge_server")


def test_health_answers_while_initialize_blocks(monkeypatch, tmp_path):
    mod = _load_bridge(
        monkeypatch,
        tmp_path,
        MT5_LOGIN="10001",
        MT5_PASSWORD="secret-demo",
        MT5_SERVER="PepperstoneUK-Demo",
    )
    gate = threading.Event()

    def slow_initialize():
        gate.wait(120)

    mod.mt5_service.initialize = slow_initialize
    started = time.perf_counter()
    with TestClient(mod.app) as client:
        response = client.get("/health")
        assert time.perf_counter() - started < 2
        body = response.json()
        assert response.status_code == 200
        assert body["state"] == "connecting"
        assert "secret-demo" not in response.text
        gate.set()


def test_ipc_timeout_schedules_another_attempt(monkeypatch, tmp_path):
    password = "secret-demo"
    mod = _load_bridge(
        monkeypatch,
        tmp_path,
        MT5_LOGIN="10001",
        MT5_PASSWORD=password,
        MT5_SERVER="PepperstoneUK-Demo",
    )

    def ipc_timeout():
        raise mod.MT5Error(-10005, f"initialize failed: IPC timeout (-10005) {password}")

    mod.mt5_service.initialize = ipc_timeout
    with TestClient(mod.app) as client:
        body = None
        text = ""
        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline:
            response = client.get("/health")
            text = response.text
            body = response.json()
            if body.get("state") == "ipc_timeout":
                break
            time.sleep(0.05)
        assert body is not None
        assert body["state"] == "ipc_timeout"
        assert body["next_retry_at"]
        nxt = datetime.fromisoformat(body["next_retry_at"])
        wait = (nxt - datetime.now(timezone.utc)).total_seconds()
        assert 10 <= wait <= 20
        assert password not in text
        assert password not in (body.get("last_error") or "")
        assert "password" not in body


def test_not_configured_does_not_retry(monkeypatch, tmp_path):
    mod = _load_bridge(monkeypatch, tmp_path)
    called = {"n": 0}

    def explode():
        called["n"] += 1
        raise AssertionError("initialize should not run when MT5 is not configured")

    mod.mt5_service.initialize = explode
    with TestClient(mod.app) as client:
        body = client.get("/health").json()
    assert body["state"] == "not_configured"
    assert body["next_retry_at"] is None
    assert called["n"] == 0
    assert "password" not in body

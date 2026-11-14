"""Automatic MT5 reconnection in the bridge (founder authorization 2026-11-14).

Runs without MetaTrader 5: the MetaTrader5 module is replaced by a fake.
"""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mt5-bridge"))
import mt5_service as ms  # noqa: E402


class FakeMT5:
    def __init__(self):
        self.ipc_alive = True
        self.init_calls = 0
        self.shutdown_calls = 0
        self.init_ok = True

    def terminal_info(self):
        return types.SimpleNamespace(connected=True, trade_allowed=True) if self.ipc_alive else None

    def account_info(self):
        return types.SimpleNamespace(login=123, server="Demo") if self.ipc_alive else None

    def initialize(self, **_kw):
        self.init_calls += 1
        if self.init_ok:
            self.ipc_alive = True
        return self.init_ok

    def shutdown(self):
        self.shutdown_calls += 1

    def last_error(self):
        return (-10005, "IPC timeout")

    def login(self, *_a, **_kw):
        return True


@pytest.fixture
def svc(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(ms, "mt5", fake)
    monkeypatch.setattr(ms, "_MT5_AVAILABLE", True)
    s = ms.MT5Service(login=123, password="x", server="Demo")
    s.initialize()
    assert s._initialized and fake.init_calls == 1
    clock = {"t": 1000.0}
    monkeypatch.setattr(ms.time, "monotonic", lambda: clock["t"])
    s._clock = clock
    s._fake = fake
    return s


def test_healthy_session_does_not_reinitialize(svc, monkeypatch):
    monkeypatch.setattr(svc, "_terminal_process_running", lambda: True)
    assert svc.ensure_connected() is True
    assert svc._fake.init_calls == 1


def test_lost_session_reconnects_when_terminal_running(svc, monkeypatch):
    monkeypatch.setattr(svc, "_terminal_process_running", lambda: True)
    svc._fake.ipc_alive = False  # MT5 closed and reopened: old IPC session gone
    assert svc.ensure_connected() is True
    assert svc._fake.init_calls == 2 and svc._initialized


def test_terminal_closed_never_launches_it(svc, monkeypatch):
    monkeypatch.setattr(svc, "_terminal_process_running", lambda: False)
    svc._fake.ipc_alive = False
    assert svc.ensure_connected() is False
    assert svc._fake.init_calls == 1  # initialize() would launch the terminal
    assert not svc._initialized
    assert "not running" in svc._last_error


def test_failed_reconnect_backs_off(svc, monkeypatch):
    monkeypatch.setattr(svc, "_terminal_process_running", lambda: True)
    svc._fake.ipc_alive = False
    svc._fake.init_ok = False
    assert svc.ensure_connected() is False
    calls = svc._fake.init_calls
    svc._clock["t"] += 31  # interval doubled to 60 s after the failure
    assert svc.ensure_connected() is False
    assert svc._fake.init_calls == calls
    svc._clock["t"] += 30
    svc._fake.init_ok = True
    assert svc.ensure_connected() is True
    assert svc._reconnect_interval == ms.RECONNECT_MIN_SECONDS


def test_unconfigured_does_nothing(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(ms, "mt5", fake)
    monkeypatch.setattr(ms, "_MT5_AVAILABLE", True)
    s = ms.MT5Service(login=0, password="", server="", configured=False)
    assert s.ensure_connected() is False
    assert fake.init_calls == 0


def test_terminal_image_names_include_configured_path():
    s = ms.MT5Service(login=1, password="", server="", terminal_path=r"C:\\MT5\\custom64.exe")
    assert s._terminal_image_names()[0] == "custom64.exe"

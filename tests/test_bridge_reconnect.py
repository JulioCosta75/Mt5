"""Automatic MT5 reconnection in the bridge (founder authorization 2026-11-14).

Runs without MetaTrader 5: the MetaTrader5 module is replaced by a fake.
"""
import subprocess
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
        self.init_ok = True
        self.init_duration = 0.0
        self.clock = None

    def terminal_info(self):
        return types.SimpleNamespace(connected=True, trade_allowed=True) if self.ipc_alive else None

    def account_info(self):
        return types.SimpleNamespace(login=123, server="Demo") if self.ipc_alive else None

    def initialize(self, **_kw):
        self.init_calls += 1
        if self.clock is not None:
            self.clock["t"] += self.init_duration  # simulate a slow IPC timeout
        if self.init_ok:
            self.ipc_alive = True
        return self.init_ok

    def shutdown(self):
        pass

    def last_error(self):
        return (-10005, "IPC timeout")

    def login(self, *_a, **_kw):
        return True


@pytest.fixture
def svc(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(ms, "mt5", fake)
    monkeypatch.setattr(ms, "_MT5_AVAILABLE", True)
    clock = {"t": 1000.0}
    monkeypatch.setattr(ms.time, "monotonic", lambda: clock["t"])
    fake.clock = clock
    s = ms.MT5Service(login=123, password="x", server="Demo")
    s.initialize()
    assert s._initialized and fake.init_calls == 1
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


def test_probe_failure_fails_closed(svc, monkeypatch):
    def boom(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd="tasklist", timeout=10)
    monkeypatch.setattr(ms.subprocess, "run", boom)
    svc._fake.ipc_alive = False
    assert svc.ensure_connected() is False
    assert svc._fake.init_calls == 1


def test_configured_path_requires_that_exact_terminal(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(ms, "mt5", fake)
    monkeypatch.setattr(ms, "_MT5_AVAILABLE", True)
    path = "/opt/Broker A/terminal64.exe"
    s = ms.MT5Service(login=123, password="x", server="Demo", terminal_path=path)
    other = types.SimpleNamespace(stdout="/opt/Broker B/terminal64.exe\n")
    monkeypatch.setattr(ms.subprocess, "run", lambda *a, **k: other)
    assert s._terminal_process_running() is False  # another broker's terminal
    mine = types.SimpleNamespace(stdout="/opt/Broker B/terminal64.exe\n/opt/Broker A/terminal64.exe\n")
    monkeypatch.setattr(ms.subprocess, "run", lambda *a, **k: mine)
    assert s._terminal_process_running() is True


def test_failed_reconnect_backs_off_from_end_of_attempt(svc, monkeypatch):
    monkeypatch.setattr(svc, "_terminal_process_running", lambda: True)
    svc._fake.ipc_alive = False
    svc._fake.init_ok = False
    svc._fake.init_duration = 165.0  # both initialize() timeouts exhausted
    assert svc.ensure_connected() is False
    calls = svc._fake.init_calls
    svc._clock["t"] += 59  # 60 s cooldown counted from the END of the attempt
    assert svc.ensure_connected() is False
    assert svc._fake.init_calls == calls
    svc._clock["t"] += 2
    svc._fake.init_ok = True
    svc._fake.init_duration = 0.0
    assert svc.ensure_connected() is True
    assert svc._reconnect_interval == ms.RECONNECT_MIN_SECONDS


def test_unconfigured_does_nothing(monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(ms, "mt5", fake)
    monkeypatch.setattr(ms, "_MT5_AVAILABLE", True)
    s = ms.MT5Service(login=0, password="", server="", configured=False)
    assert s.ensure_connected() is False
    assert fake.init_calls == 0


def test_recorder_schedules_an_active_reconnect_job():
    pytest.importorskip("apscheduler")
    import snapshot_recorder as sr

    class Svc:
        login = 1

        def ensure_connected(self):
            return True

    rec = sr.SnapshotRecorder(Svc(), storage=None, interval_seconds=10)
    rec.start()
    try:
        job = rec._reconnect_job
        assert job is not None and job.next_run_time is not None  # active, not paused
        assert job.trigger.interval.total_seconds() == sr.RECONNECT_CHECK_SECONDS
    finally:
        rec.stop()

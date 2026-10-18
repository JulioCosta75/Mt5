"""IPC candidates and the read-only MT5 diagnostic. No terminal, no credentials."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "mt5-bridge"
SCRIPT = ROOT / "installer" / "scripts" / "diagnose_mt5.py"


def _load_diagnose():
    spec = importlib.util.spec_from_file_location("diagnose_mt5", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_candidates():
    sys.path.insert(0, str(BRIDGE))
    sys.modules.pop("ipc_candidates", None)
    return importlib.import_module("ipc_candidates")


def test_diagnostic_runs_without_credentials(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-initialize"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "package:" in out
    assert "port 127.0.0.1:22346:" in out
    assert "initialize: skipped" in out
    assert "password" not in out.lower()
    assert not list(tmp_path.iterdir())


def test_diagnostic_rejects_credentials():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--password", "secret-demo"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 2
    assert "secret-demo" not in proc.stdout
    assert "secret-demo" not in proc.stderr


def test_journal_helpers_hide_secrets_and_keep_company():
    diag = _load_diagnose()
    text = "\n".join(
        [
            "Pepperstone MetaTrader 5 x64 build 6230 started for Pepperstone Limited",
            "password=secret-demo",
            "MCP started on 127.0.0.1:22346",
        ]
    )
    tail = diag.tail_lines(text, 30)
    assert any("Pepperstone Limited" in line for line in tail)
    assert all("secret-demo" not in line for line in tail)
    assert diag.company_lines(text) == [
        "Pepperstone MetaTrader 5 x64 build 6230 started for Pepperstone Limited"
    ]
    assert diag.experts_keys("[Common]\nFoo=1\n[Experts]\nEnabled=1\nApi=0\n") == {
        "Enabled": "1",
        "Api": "0",
    }
    def _reject(**kwargs):
        raise RuntimeError("secret-demo")

    probe = diag.probe_initialize(
        types.SimpleNamespace(
            initialize=_reject,
            last_error=lambda: (-1, ""),
            shutdown=lambda: None,
        ),
        path="C:/MT5/terminal64.exe",
        password="secret-demo",
        login=1,
        server="PepperstoneUK-Demo",
    )
    assert "secret-demo" not in probe
    assert probe.startswith("raised ")


def test_probe_reports_initialize_without_keeping_secrets():
    diag = _load_diagnose()
    seen = {}

    def initialize(**kwargs):
        seen.update(kwargs)
        return True

    mt5 = types.SimpleNamespace(
        initialize=initialize,
        last_error=lambda: (1, "ok"),
        version=lambda: (5, 6230, "17 Oct 2026"),
        shutdown=lambda: None,
    )
    text = diag.probe_initialize(mt5, path="C:/MT5/terminal64.exe", portable=True, password="secret-demo")
    assert seen["path"] == "C:/MT5/terminal64.exe"
    assert seen["portable"] is True
    assert "password" not in seen
    assert "secret-demo" not in text
    assert "ok=True" in text
    assert "6230" in text


def test_servers_dat_is_off_unless_selected(tmp_path, monkeypatch):
    mod = _load_candidates()
    monkeypatch.delenv("ATLAS_IPC_CANDIDATE", raising=False)
    monkeypatch.delenv("ATLAS_MT5_SERVERS_DAT", raising=False)
    monkeypatch.delenv("ATLAS_MT5_DATA_DIR", raising=False)
    assert mod.prepare_initialize() == {}
    assert not (tmp_path / "config" / "servers.dat").exists()


def test_servers_dat_copies_only_that_file(tmp_path, monkeypatch):
    mod = _load_candidates()
    source = tmp_path / "servers.dat"
    source.write_bytes(b"server-list")
    data = tmp_path / "fresh"
    monkeypatch.setenv("ATLAS_IPC_CANDIDATE", "servers-dat")
    monkeypatch.setenv("ATLAS_MT5_SERVERS_DAT", str(source))
    monkeypatch.setenv("ATLAS_MT5_DATA_DIR", str(data))
    assert mod.prepare_initialize() == {"portable": True}
    assert (data / "config" / "servers.dat").read_bytes() == b"server-list"

    accounts = tmp_path / "accounts.dat"
    accounts.write_bytes(b"secret-demo")
    monkeypatch.setenv("ATLAS_MT5_SERVERS_DAT", str(accounts))
    with pytest.raises(ValueError, match="servers.dat"):
        mod.prepare_initialize()
    assert not (data / "config" / "accounts.dat").exists()


def test_user_step_candidates_do_not_write(tmp_path, monkeypatch):
    mod = _load_candidates()
    monkeypatch.chdir(tmp_path)
    for mode in ("broker-terminal", "open-account"):
        monkeypatch.setenv("ATLAS_IPC_CANDIDATE", mode)
        assert mod.prepare_initialize() == {}
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setenv("ATLAS_IPC_CANDIDATE", "downgrade")
    with pytest.raises(ValueError):
        mod.prepare_initialize()


def test_initialize_uses_portable_only_when_the_candidate_is_on(tmp_path, monkeypatch):
    source = tmp_path / "servers.dat"
    source.write_bytes(b"server-list")
    data = tmp_path / "fresh"
    calls = []

    fake = types.ModuleType("MetaTrader5")

    def initialize(**kwargs):
        calls.append(dict(kwargs))
        return False

    fake.initialize = initialize
    fake.last_error = lambda: (-10005, "IPC timeout")
    fake.shutdown = lambda: None
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    sys.path.insert(0, str(BRIDGE))
    for name in ("mt5_service", "ipc_candidates"):
        sys.modules.pop(name, None)
    try:
        service = importlib.import_module("mt5_service")
        bridge = service.MT5Service(10001, "secret-demo", "PepperstoneUK-Demo", configured=True)
        monkeypatch.delenv("ATLAS_IPC_CANDIDATE", raising=False)
        with pytest.raises(service.MT5Error):
            bridge.initialize()
        assert calls
        assert all("portable" not in call for call in calls)
        assert calls[0].keys() <= {"timeout", "path"}

        calls.clear()
        monkeypatch.setenv("ATLAS_IPC_CANDIDATE", "servers-dat")
        monkeypatch.setenv("ATLAS_MT5_SERVERS_DAT", str(source))
        monkeypatch.setenv("ATLAS_MT5_DATA_DIR", str(data))
        sys.modules.pop("ipc_candidates", None)
        importlib.reload(service)
        bridge = service.MT5Service(10001, "secret-demo", "PepperstoneUK-Demo", configured=True)
        with pytest.raises(service.MT5Error):
            bridge.initialize()
        assert calls and all(call.get("portable") is True for call in calls)
        copied = (data / "config" / "servers.dat").read_bytes()
        assert copied == b"server-list"
        assert b"secret-demo" not in copied
    finally:
        sys.modules.pop("mt5_service", None)
        sys.modules.pop("ipc_candidates", None)
        while str(BRIDGE) in sys.path:
            sys.path.remove(str(BRIDGE))

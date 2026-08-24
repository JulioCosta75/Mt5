"""Unit tests for installer/scripts/atlas_launcher.py (no Windows / no MT5 required)."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "installer" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import atlas_launcher as al  # noqa: E402


def _make_fake_root(tmp_path: Path, *, bridge_name: str = "bridge") -> Path:
    root = tmp_path / "Atlas"
    (root / "backend").mkdir(parents=True)
    (root / bridge_name).mkdir(parents=True)
    (root / "backend" / "server.py").write_text("# fake\n", encoding="utf-8")
    (root / bridge_name / "bridge_server.py").write_text("# fake\n", encoding="utf-8")
    (root / "data").mkdir()
    (root / "logs").mkdir()
    return root


def test_resolve_paths_prefers_explicit_root(tmp_path, monkeypatch):
    root = _make_fake_root(tmp_path)
    monkeypatch.delenv("ATLAS_ROOT", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    paths = al.resolve_paths(str(root))
    assert paths.root == root
    assert paths.bridge == root / "bridge"
    assert paths.backend == root / "backend"


def test_resolve_paths_dev_layout_mt5_bridge(tmp_path, monkeypatch):
    root = _make_fake_root(tmp_path, bridge_name="mt5-bridge")
    monkeypatch.delenv("ATLAS_ROOT", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    paths = al.resolve_paths(str(root))
    assert paths.bridge == root / "mt5-bridge"


def test_resolve_paths_localappdata(tmp_path, monkeypatch):
    local = tmp_path / "Local"
    root = _make_fake_root(local)
    # _make_fake_root created local/Atlas
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.delenv("ATLAS_ROOT", raising=False)
    paths = al.resolve_paths(None)
    assert paths.root == root


def test_child_restart_exhausted(tmp_path, monkeypatch):
    root = _make_fake_root(tmp_path)
    py = sys.executable
    # Immediate-exit child to exercise restart budget.
    spec = al.ChildSpec(
        name="Boom",
        cwd=root,
        args=[py, "-c", "import sys; sys.exit(7)"],
        env=os.environ.copy(),
        out_log=root / "logs" / "boom.out.log",
        err_log=root / "logs" / "boom.err.log",
    )
    child = al.ChildHandle(spec)
    child.start()
    # Wait until first exit.
    for _ in range(50):
        if child.proc and child.proc.poll() is not None:
            break
        time.sleep(0.05)
    assert child.proc is not None and child.proc.poll() is not None

    # Burn through MAX_RESTARTS successful restart attempts + final failure.
    last_err = None
    for _ in range(al.MAX_RESTARTS + 2):
        # Ensure process has exited before noting.
        for _ in range(50):
            if child.proc is None or child.proc.poll() is not None:
                break
            time.sleep(0.05)
        err = child.note_exit_and_maybe_restart()
        if err:
            last_err = err
            break
        # Newly started process will exit again quickly.
        time.sleep(0.2)
    assert last_err is not None
    assert child.gave_up is True
    assert "restart" in last_err.lower() or "failed" in last_err.lower()


def test_launcher_builds_expected_commands(tmp_path, monkeypatch):
    root = _make_fake_root(tmp_path)
    paths = al.resolve_paths(str(root))
    # Force interpreter to current python for assertion stability.
    paths = al.AtlasPaths(
        root=paths.root,
        backend=paths.backend,
        bridge=paths.bridge,
        frontend_build=paths.frontend_build,
        data=paths.data,
        logs=paths.logs,
        python=Path(sys.executable),
        icon=paths.icon,
    )
    launcher = al.Launcher(paths, open_browser=False)
    children = launcher.build_children()
    names = [c.spec.name for c in children]
    assert names == ["AtlasBridge", "AtlasBackend"]
    assert children[0].spec.args[-1] == "bridge_server.py"
    assert "uvicorn" in children[1].spec.args
    assert children[1].spec.env["SERVE_FRONTEND"] == "true"
    assert children[1].spec.env["ATLAS_STORE"] == "sqlite"


def test_open_dashboard_once_per_session(tmp_path, monkeypatch):
    root = _make_fake_root(tmp_path)
    paths = al.resolve_paths(str(root))
    launcher = al.Launcher(paths, open_browser=False)
    opens: list[str] = []
    monkeypatch.setattr(
        al, "open_dashboard_url", lambda url=al.BACKEND_URL: opens.append(url) or "default"
    )

    assert launcher.open_dashboard(force=False) is True
    assert launcher.open_dashboard(force=False) is False
    assert launcher.open_dashboard(force=False) is False
    # Manual tray action may force a new tab.
    assert launcher.open_dashboard(force=True) is True
    assert opens == [al.BACKEND_URL, al.BACKEND_URL]

    # restart_all must not clear the session flag / open tabs
    launcher.children = []
    launcher.restart_all()
    assert launcher.open_dashboard(force=False) is False
    assert opens == [al.BACKEND_URL, al.BACKEND_URL]


def test_open_dashboard_url_falls_back_to_edge(tmp_path, monkeypatch):
    edge = tmp_path / "msedge.exe"
    edge.write_bytes(b"")
    monkeypatch.setattr(al, "has_default_http_handler", lambda: True)
    monkeypatch.setattr(al, "open_url_via_default_handler", lambda url: False)
    monkeypatch.setattr(al, "edge_browser_candidates", lambda: [edge])
    launches: list[list[str]] = []

    def fake_popen(args, **kwargs):
        launches.append(list(args))
        return None

    monkeypatch.setattr(al.subprocess, "Popen", fake_popen)
    assert al.open_dashboard_url("http://localhost:8001/") == "edge"
    assert launches == [[str(edge), "http://localhost:8001/"]]


def test_open_dashboard_url_skips_default_when_no_userchoice(tmp_path, monkeypatch):
    """No http UserChoice ProgId → never call startfile; go straight to Edge."""
    edge = tmp_path / "msedge.exe"
    edge.write_bytes(b"")
    default_calls: list[str] = []
    monkeypatch.setattr(al, "has_default_http_handler", lambda: False)
    monkeypatch.setattr(
        al,
        "open_url_via_default_handler",
        lambda url: default_calls.append(url) or True,
    )
    monkeypatch.setattr(al, "edge_browser_candidates", lambda: [edge])
    launches: list[list[str]] = []
    monkeypatch.setattr(
        al.subprocess, "Popen", lambda args, **kwargs: launches.append(list(args))
    )
    assert al.open_dashboard_url("http://localhost:8001/") == "edge"
    assert default_calls == []
    assert launches == [[str(edge), "http://localhost:8001/"]]


def test_open_dashboard_url_shows_message_when_default_and_edge_fail(monkeypatch):
    monkeypatch.setattr(al, "has_default_http_handler", lambda: True)
    monkeypatch.setattr(al, "open_url_via_default_handler", lambda url: False)
    monkeypatch.setattr(al, "edge_browser_candidates", lambda: [])
    shown: list[bool] = []
    monkeypatch.setattr(al, "show_dashboard_open_hint", lambda: shown.append(True))
    assert al.open_dashboard_url("http://localhost:8001/") == "message"
    assert shown == [True]


def test_open_dashboard_url_uses_default_when_available(monkeypatch):
    monkeypatch.setattr(al, "has_default_http_handler", lambda: True)
    monkeypatch.setattr(al, "open_url_via_default_handler", lambda url: True)
    called = {"edge": False, "msg": False}
    monkeypatch.setattr(
        al, "open_url_via_edge", lambda url: called.__setitem__("edge", True) or True
    )
    monkeypatch.setattr(
        al, "show_dashboard_open_hint", lambda: called.__setitem__("msg", True)
    )
    assert al.open_dashboard_url("http://localhost:8001/") == "default"
    assert called == {"edge": False, "msg": False}


def test_open_url_via_default_handler_oserror_is_failure(monkeypatch):
    def boom(url):
        raise OSError(1155, "No application is associated")

    monkeypatch.setattr(al.sys, "platform", "win32")
    monkeypatch.setattr(al.os, "startfile", boom, raising=False)
    assert al.open_url_via_default_handler("http://localhost:8001/") is False


def test_has_default_http_handler_non_windows(monkeypatch):
    monkeypatch.setattr(al.sys, "platform", "linux")
    assert al.has_default_http_handler() is True


def test_has_default_http_handler_missing_userchoice(monkeypatch):
    class FakeWinreg:
        HKEY_CURRENT_USER = object()

        def OpenKey(self, *_args, **_kwargs):
            raise OSError(2, "The system cannot find the file specified")

    monkeypatch.setattr(al.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg())
    assert al.has_default_http_handler() is False


def test_has_default_http_handler_empty_progid(monkeypatch):
    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = object()

        def OpenKey(self, *_args, **_kwargs):
            return FakeKey()

        def QueryValueEx(self, _key, name):
            assert name == "ProgId"
            return ("", 1)

    monkeypatch.setattr(al.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg())
    assert al.has_default_http_handler() is False


def test_has_default_http_handler_with_progid(monkeypatch):
    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = object()

        def OpenKey(self, *_args, **_kwargs):
            return FakeKey()

        def QueryValueEx(self, _key, name):
            assert name == "ProgId"
            return ("MSEdgeHTM", 1)

    monkeypatch.setattr(al.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg())
    assert al.has_default_http_handler() is True

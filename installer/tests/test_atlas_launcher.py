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

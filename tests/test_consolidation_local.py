#!/usr/bin/env python3
"""Local validation for consolidated branch (bridge UNCONFIGURED + installer config)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_bridge_unconfigured_health():
    """MT5 Bridge must boot without credentials and report unconfigured."""
    bridge_dir = ROOT / "mt5-bridge"
    env = os.environ.copy()
    env.pop("MT5_LOGIN", None)
    env.pop("MT5_PASSWORD", None)
    env.pop("MT5_SERVER", None)
    env.pop("BRIDGE_TOKEN", None)

    # Load config without .env
    spec_cfg = importlib.util.spec_from_file_location("bridge_config", bridge_dir / "config.py")
    cfg_mod = importlib.util.module_from_spec(spec_cfg)
    sys.modules["bridge_config"] = cfg_mod
    spec_cfg.loader.exec_module(cfg_mod)

    settings = cfg_mod.Settings.load()
    assert settings.configured is False
    assert settings.mt5_login == 0

    spec_svc = importlib.util.spec_from_file_location("mt5_service", bridge_dir / "mt5_service.py")
    svc_mod = importlib.util.module_from_spec(spec_svc)
    sys.modules["mt5_service"] = svc_mod
    spec_svc.loader.exec_module(svc_mod)

    svc = svc_mod.MT5Service(0, "", "", configured=False)
    svc.initialize()  # must not raise
    health = svc.health()
    assert health["status"] == "unconfigured"
    assert health["configured"] is False
    assert health["terminal_connected"] is False
    print("✅ bridge UNCONFIGURED health:", health["status"])


def test_configure_atlas_writes_env_files():
    """Installer configure_atlas.py must write bridge/backend .env and dashboard json."""
    script = ROOT / "installer" / "scripts" / "configure_atlas.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        backend = tmp_path / "backend"
        bridge = tmp_path / "bridge"
        data = tmp_path / "data"
        answers = tmp_path / "answers.json"
        answers.write_text(
            json.dumps(
                {
                    "login": "12345678",
                    "password": "secret123",
                    "server": "Darwinex-Live",
                    "terminal_path": "",
                    "bridge_port": 8002,
                }
            ),
            encoding="utf-8",
        )
        rc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--answers",
                str(answers),
                "--non-interactive",
                "--backend-dir",
                str(backend),
                "--bridge-dir",
                str(bridge),
                "--data-dir",
                str(data),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert rc.returncode == 0, rc.stderr + rc.stdout

        bridge_env = (bridge / ".env").read_text(encoding="utf-8")
        backend_env = (backend / ".env").read_text(encoding="utf-8")
        dashboard = json.loads((data / "mt5_config.json").read_text(encoding="utf-8"))

        assert "MT5_LOGIN=12345678" in bridge_env
        assert "MT5_PASSWORD=secret123" in bridge_env
        assert "MT5_SERVER=Darwinex-Live" in bridge_env
        assert "BRIDGE_TOKEN=" in bridge_env
        assert "MT5_BRIDGE_URL=http://127.0.0.1:8002" in backend_env
        assert dashboard["configured"] is True
        assert dashboard["login"] == "12345678"
        print("✅ configure_atlas.py wrote bridge/backend .env and dashboard json")


def test_dashboard_backend_api_smoke():
    """Dashboard API client endpoints must respond on running backend."""
    import requests

    base = os.environ.get("REACT_APP_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
    api = f"{base}/api"
    r1 = requests.get(f"{api}/kpis", timeout=5)
    r2 = requests.get(f"{api}/accounts", timeout=5)
    r3 = requests.get(f"{api}/system/version", timeout=5)
    assert r1.status_code == 200 and r1.json()["accounts_total"] == 8
    assert r2.status_code == 200 and len(r2.json()) == 8
    assert r3.status_code == 200 and r3.json()["version"] == "0.3.0"
    print("✅ dashboard backend API smoke OK")


if __name__ == "__main__":
    test_bridge_unconfigured_health()
    test_configure_atlas_writes_env_files()
    test_dashboard_backend_api_smoke()
    print("\n🎉 ALL CONSOLIDATION LOCAL VALIDATIONS PASSED")

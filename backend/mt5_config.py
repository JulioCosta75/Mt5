"""MT5 connection configuration — managed from the Dashboard.

Stores the MetaTrader 5 connection settings that used to be collected by the
one-time install wizard. The dashboard can now read, update and clear these
settings at any time (no reinstall required).

Storage model
--------------
* A JSON file (``mt5_config.json``) in the Atlas data directory is the
  dashboard-facing source of truth (used to prefill the form + show status).
* On a Windows installation (os.name == 'nt') the same settings are ALSO
  written to ``bridge/.env`` and ``backend/.env`` and the Atlas Windows
  services are restarted so the new credentials take effect. On non-Windows
  (the Emergent Linux preview) only the JSON file is written.

Credentials are kept locally on the machine only — Atlas never transmits them
anywhere itself.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
# Install root on Windows = parent of backend dir ({app}\backend -> {app}).
INSTALL_ROOT = BACKEND_DIR.parent


def _data_dir() -> Path:
    explicit = os.environ.get("ATLAS_DATA_DIR")
    if explicit:
        d = Path(explicit)
    else:
        sqlite_path = os.environ.get("ATLAS_SQLITE_PATH")
        d = Path(sqlite_path).parent if sqlite_path else (BACKEND_DIR / "data")
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    override = os.environ.get("ATLAS_CONFIG_PATH")
    return Path(override) if override else (_data_dir() / "mt5_config.json")


DEFAULTS = {
    "configured": False,
    "login": "",
    "password": "",
    "server": "",
    "terminal_path": "",
    "bridge_host": "127.0.0.1",
    "bridge_port": 8002,
    "bridge_token": "",
    "updated_at": None,
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    p = config_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: data.get(k, cfg[k]) for k in cfg})
        except Exception:
            pass
    return cfg


def _save(cfg: dict) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def masked(cfg: dict) -> dict:
    """Config safe to send to the browser — password is never returned."""
    out = {k: cfg.get(k) for k in DEFAULTS if k != "password"}
    out["password_set"] = bool(cfg.get("password"))
    return out


class ConfigError(ValueError):
    pass


def validate(payload: dict) -> None:
    login = str(payload.get("login", "")).strip()
    if not login.isdigit():
        raise ConfigError("MT5 login must be a number.")
    if not str(payload.get("password", "")).strip():
        raise ConfigError("MT5 password is required.")
    if not str(payload.get("server", "")).strip():
        raise ConfigError("MT5 server / broker is required (e.g. Darwinex-Live).")
    port = payload.get("bridge_port", 8002)
    try:
        port_i = int(port)
        if not (1 <= port_i <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        raise ConfigError("Bridge port must be a valid port number (1-65535).")


def save_config(payload: dict) -> dict:
    """Validate + persist. Keeps existing password if payload omits it.

    Returns the (unmasked) stored config dict.
    """
    validate_payload = dict(payload)
    existing = load()
    # Allow keeping the existing password when the form sends an empty value.
    if not str(validate_payload.get("password", "")).strip() and existing.get("password"):
        validate_payload["password"] = existing["password"]
    validate(validate_payload)

    token = str(validate_payload.get("bridge_token") or existing.get("bridge_token") or "").strip()
    if not token:
        token = secrets.token_urlsafe(32)

    cfg = {
        "configured": True,
        "login": str(validate_payload["login"]).strip(),
        "password": str(validate_payload["password"]),
        "server": str(validate_payload["server"]).strip(),
        "terminal_path": str(validate_payload.get("terminal_path", "") or "").strip(),
        "bridge_host": str(validate_payload.get("bridge_host", "127.0.0.1") or "127.0.0.1").strip(),
        "bridge_port": int(validate_payload.get("bridge_port", 8002)),
        "bridge_token": token,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not cfg["terminal_path"] and os.name == "nt":
        detected = _auto_terminal_path()
        if detected:
            cfg["terminal_path"] = detected
    _save(cfg)
    return cfg


def clear_config() -> dict:
    cfg = dict(DEFAULTS)
    cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(cfg)
    # On Windows, also blank the bridge .env so the bridge stops connecting.
    if os.name == "nt":
        try:
            _write_backend_env(mt5_bridge_url="", token="")
            _write_bridge_env(cfg, disabled=True)
            _restart_services()
        except Exception:
            pass
    return cfg


# ---------------------------------------------------------------------------
# Windows-only: write the .env files the services read, then restart them.
# ---------------------------------------------------------------------------
def _bridge_dir() -> Path:
    # Production layout: {app}\bridge ; dev layout: <repo>\mt5-bridge
    cand = INSTALL_ROOT / "bridge"
    if cand.exists():
        return cand
    return INSTALL_ROOT / "mt5-bridge"


def _auto_terminal_path() -> str:
    bridge = _bridge_dir()
    helper = bridge / "mt5_terminal.py"
    if not helper.is_file():
        return ""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("atlas_mt5_terminal", helper)
        if not spec or not spec.loader:
            return ""
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        path, _ = mod.resolve_terminal_path(None)
        return path or ""
    except Exception:
        return ""


def _write_bridge_env(cfg: dict, disabled: bool = False) -> None:
    bridge = _bridge_dir()
    bridge.mkdir(parents=True, exist_ok=True)
    data_dir = _data_dir()
    if disabled:
        content = "# MT5 connection cleared from the Atlas dashboard.\n"
    else:
        terminal_path = str(cfg.get("terminal_path", "") or "").strip()
        if not terminal_path:
            terminal_path = _auto_terminal_path()
            if terminal_path:
                cfg["terminal_path"] = terminal_path
        lines = [
            f"MT5_LOGIN={cfg['login']}",
            f"MT5_PASSWORD={cfg['password']}",
            f"MT5_SERVER={cfg['server']}",
        ]
        if terminal_path:
            lines.append(f"MT5_TERMINAL_PATH={terminal_path}")
        lines += [
            f"BRIDGE_TOKEN={cfg['bridge_token']}",
            f"BRIDGE_HOST={cfg.get('bridge_host', '127.0.0.1')}",
            f"BRIDGE_PORT={cfg['bridge_port']}",
            "SNAPSHOT_INTERVAL_SECONDS=10",
            f"SQLITE_PATH={data_dir / 'bridge_data.db'}",
            "LOG_LEVEL=INFO",
        ]
        content = "\n".join(lines) + "\n"
    (bridge / ".env").write_text(content, encoding="utf-8")


def _write_backend_env(mt5_bridge_url: str, token: str) -> None:
    data_dir = _data_dir()
    frontend_build = INSTALL_ROOT / "frontend_build"
    lines = [
        f"MT5_BRIDGE_URL={mt5_bridge_url}",
        f"MT5_BRIDGE_TOKEN={token}",
        "ATLAS_STORE=sqlite",
        f"ATLAS_SQLITE_PATH={data_dir / 'atlas.db'}",
        "SERVE_FRONTEND=true",
        f"FRONTEND_BUILD={frontend_build}",
        "CORS_ORIGINS=*",
    ]
    (BACKEND_DIR / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _restart_services() -> None:
    """Fire-and-forget restart of the Atlas services (Windows only).

    Runs a detached helper so this backend process can finish responding to the
    HTTP request before it is itself restarted.
    """
    scripts = INSTALL_ROOT / "scripts"
    restart_bat = scripts / "apply_restart.bat"
    if restart_bat.exists():
        subprocess.Popen(
            ["cmd.exe", "/c", str(restart_bat)],
            cwd=str(scripts),
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True,
        )


def apply_to_windows(cfg: dict) -> bool:
    """Write .env files + restart services on Windows. Returns True if applied."""
    if os.name != "nt":
        return False
    bridge_url = f"http://127.0.0.1:{cfg['bridge_port']}"
    _write_bridge_env(cfg)
    _write_backend_env(bridge_url, cfg["bridge_token"])
    _restart_services()
    return True

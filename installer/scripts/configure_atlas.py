"""Atlas first-run configuration.

Collects the MetaTrader 5 credentials and writes the configuration files the
Atlas services read, so the bridge connects to MT5 immediately after
installation with no manual editing:

  * ``<bridge>/.env``   -> read by mt5-bridge/bridge_server.py
  * ``<backend>/.env``  -> read by the Atlas backend (bridge URL + token)
  * ``<data>/mt5_config.json`` -> dashboard-facing config (keeps the Settings
                                   page in sync with what the installer wrote)

Modes
-----
* Interactive (default): prompts for MT5 login / password / server / path.
* Non-interactive: supply values via --answers <json>, CLI flags, or the
  environment variables ATLAS_MT5_LOGIN / ATLAS_MT5_PASSWORD /
  ATLAS_MT5_SERVER / ATLAS_MT5_PATH (handy for silent installs).

Layout-aware: works from a production install ({app}\backend, {app}\bridge)
and from a fresh git clone (<repo>\backend, <repo>\mt5-bridge). Directories
can also be overridden explicitly with --backend-dir / --bridge-dir /
--data-dir (used by the Windows installer).

Exit codes: 0 = configured (or already configured), 1 = aborted / invalid.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
def resolve_layout(args) -> dict:
    """Return {root, backend, bridge, data} honouring explicit overrides."""
    scripts_dir = Path(__file__).resolve().parent
    # One level up is {app} (production) or <repo>/installer (git clone).
    up = scripts_dir.parent

    if (up / "backend" / "server.py").exists():
        # Production layout: {app}\scripts, {app}\backend, {app}\bridge
        root = up
        backend = up / "backend"
        bridge = up / "bridge"
    else:
        # Fresh clone: <repo>\installer\scripts -> <repo>
        root = up.parent
        backend = root / "backend"
        bridge = root / "mt5-bridge"

    if args.backend_dir:
        backend = Path(args.backend_dir)
    if args.bridge_dir:
        bridge = Path(args.bridge_dir)
    data = Path(args.data_dir) if args.data_dir else (root / "data")
    return {"root": root, "backend": backend, "bridge": bridge, "data": data}


def frontend_build_dir(root: Path) -> Path:
    for cand in (root / "frontend_build", root / "frontend" / "build"):
        if cand.exists():
            return cand
    return root / "frontend_build"


# ---------------------------------------------------------------------------
# Reading existing values (idempotency + token reuse)
# ---------------------------------------------------------------------------
def parse_env(path: Path) -> dict:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    except Exception:
        pass
    return out


def existing_token(paths: dict) -> str:
    for p, key in (
        (paths["bridge"] / ".env", "BRIDGE_TOKEN"),
        (paths["backend"] / ".env", "MT5_BRIDGE_TOKEN"),
    ):
        val = parse_env(p).get(key, "").strip()
        if val:
            return val
    cfg = paths["data"] / "mt5_config.json"
    if cfg.exists():
        try:
            return str(json.loads(cfg.read_text(encoding="utf-8")).get("bridge_token", "")).strip()
        except Exception:
            pass
    return ""


def already_configured(paths: dict) -> bool:
    return bool(parse_env(paths["bridge"] / ".env").get("MT5_LOGIN", "").strip())


# ---------------------------------------------------------------------------
# Gathering answers
# ---------------------------------------------------------------------------
class ConfigError(ValueError):
    pass


def validate(a: dict) -> None:
    if not str(a.get("login", "")).strip().isdigit():
        raise ConfigError("MT5 login must be a number.")
    if not str(a.get("password", "")).strip():
        raise ConfigError("MT5 password is required.")
    if not str(a.get("server", "")).strip():
        raise ConfigError("MT5 server / broker is required (e.g. Darwinex-Live).")
    try:
        port = int(a.get("bridge_port", 8002))
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        raise ConfigError("Bridge port must be a valid port number (1-65535).")


def load_dashboard(paths: dict) -> dict:
    """Return the dashboard-saved config (mt5_config.json), or {} if absent."""
    p = paths["data"] / "mt5_config.json"
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def has_min(a: dict) -> bool:
    return bool(str(a.get("login", "")).strip()
                and str(a.get("password", "")).strip()
                and str(a.get("server", "")).strip())


def answers_from_sources(args) -> dict:
    """Collect answers from --answers file / flags / env (non-interactive)."""
    a: dict = {}
    if args.answers and Path(args.answers).exists():
        try:
            data = json.loads(Path(args.answers).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                a.update(data)
        except Exception:
            pass
    # CLI flags and env vars override the answers file.
    mapping = {
        "login": (args.login, "ATLAS_MT5_LOGIN"),
        "password": (args.password, "ATLAS_MT5_PASSWORD"),
        "server": (args.server, "ATLAS_MT5_SERVER"),
        "terminal_path": (args.path, "ATLAS_MT5_PATH"),
        "bridge_port": (args.bridge_port, "ATLAS_BRIDGE_PORT"),
    }
    for key, (flag, env) in mapping.items():
        if flag is not None:
            a[key] = flag
        elif os.environ.get(env):
            a[key] = os.environ[env]
    return a


def prompt_answers(existing: dict) -> dict:
    print("")
    print("=" * 60)
    print("  Atlas - MetaTrader 5 account setup")
    print("=" * 60)
    print("  Credentials are stored locally on this machine only.")
    print("  Atlas never transmits them anywhere itself.")
    print("")

    def ask(label: str, default: str = "", *, secret: bool = False, required: bool = True) -> str:
        suffix = f" [{default}]" if default else ""
        while True:
            if secret:
                val = getpass.getpass(f"  {label}{suffix}: ").strip()
            else:
                val = input(f"  {label}{suffix}: ").strip()
            if not val and default:
                val = default
            if val or not required:
                return val
            print("    ! This field is required.")

    a: dict = {}
    a["login"] = ask("MT5 login (number) - leave blank to skip and set up later",
                      existing.get("login", ""), required=False)
    if not a["login"].strip():
        return {}  # user chose to skip
    a["password"] = ask("MT5 password", secret=True)
    a["server"] = ask("MT5 server / broker (e.g. Darwinex-Live)", existing.get("server", ""))
    a["terminal_path"] = ask(
        "MT5 terminal path (terminal64.exe) - optional, blank = auto-detect",
        existing.get("terminal_path", ""),
        required=False,
    )
    a["bridge_port"] = ask("Bridge port", str(existing.get("bridge_port", 8002)), required=False) or "8002"
    return a


# ---------------------------------------------------------------------------
# Writing config
# ---------------------------------------------------------------------------
def auto_terminal_path(bridge_dir: Path) -> str:
    """Detect terminal64.exe on Windows (running process preferred)."""
    helper = bridge_dir / "mt5_terminal.py"
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


def write_bridge_env(paths: dict, cfg: dict) -> Path:
    bridge = paths["bridge"]
    bridge.mkdir(parents=True, exist_ok=True)
    terminal_path = str(cfg.get("terminal_path", "") or "").strip()
    if not terminal_path:
        terminal_path = auto_terminal_path(bridge)
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
        f"SQLITE_PATH={paths['data'] / 'bridge_data.db'}",
        "LOG_LEVEL=INFO",
    ]
    p = bridge / ".env"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def write_backend_env(paths: dict, cfg: dict) -> Path:
    backend = paths["backend"]
    backend.mkdir(parents=True, exist_ok=True)
    lines = [
        f"MT5_BRIDGE_URL=http://127.0.0.1:{cfg['bridge_port']}",
        f"MT5_BRIDGE_TOKEN={cfg['bridge_token']}",
        "ATLAS_STORE=sqlite",
        f"ATLAS_SQLITE_PATH={paths['data'] / 'atlas.db'}",
        "SERVE_FRONTEND=true",
        f"FRONTEND_BUILD={frontend_build_dir(paths['root'])}",
        "CORS_ORIGINS=*",
    ]
    p = backend / ".env"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def write_dashboard_json(paths: dict, cfg: dict) -> Path:
    data = paths["data"]
    data.mkdir(parents=True, exist_ok=True)
    doc = {
        "configured": True,
        "login": cfg["login"],
        "password": cfg["password"],
        "server": cfg["server"],
        "terminal_path": cfg.get("terminal_path", ""),
        "bridge_host": cfg.get("bridge_host", "127.0.0.1"),
        "bridge_port": int(cfg["bridge_port"]),
        "bridge_token": cfg["bridge_token"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    p = data / "mt5_config.json"
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Configure Atlas MT5 credentials.")
    p.add_argument("--login")
    p.add_argument("--password")
    p.add_argument("--server")
    p.add_argument("--path", help="Full path to terminal64.exe (optional)")
    p.add_argument("--bridge-port", dest="bridge_port")
    p.add_argument("--answers", help="Path to a JSON file with the answers")
    p.add_argument("--backend-dir")
    p.add_argument("--bridge-dir")
    p.add_argument("--data-dir")
    p.add_argument("--non-interactive", action="store_true",
                   help="Never prompt; fail if required values are missing.")
    p.add_argument("--force", action="store_true",
                   help="Reconfigure even if a .env already exists.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = resolve_layout(args)

    supplied = answers_from_sources(args)
    provided = has_min(supplied)
    restored = False

    if provided:
        a = supplied
    elif args.non_interactive:
        # No new credentials were supplied. On a reinstall/upgrade the bridge
        # .env may have been wiped, but the dashboard-saved config survives —
        # restore from it so Atlas reconnects automatically with zero re-entry.
        doc = load_dashboard(paths)
        if doc.get("configured") and has_min(doc):
            a = {
                "login": doc.get("login", ""),
                "password": doc.get("password", ""),
                "server": doc.get("server", ""),
                "terminal_path": doc.get("terminal_path", ""),
                "bridge_host": doc.get("bridge_host", "127.0.0.1"),
                "bridge_port": doc.get("bridge_port", 8002),
            }
            restored = True
        else:
            print("[configure_atlas] No MT5 credentials supplied and none saved "
                  "yet - leaving unconfigured (set it up from the dashboard).")
            return 0
    else:
        # Interactive console.
        if already_configured(paths) and not args.force:
            print("[configure_atlas] Already configured ("
                  + str(paths["bridge"] / ".env")
                  + "). Re-run with --force to change it.")
            return 0
        if not sys.stdin or not sys.stdin.isatty():
            print("[configure_atlas] ERROR: no credentials supplied and no "
                  "interactive console available (use --answers or flags, or "
                  "--non-interactive).", file=sys.stderr)
            return 1
        a = prompt_answers(load_dashboard(paths))
        if not has_min(a):
            print("[configure_atlas] Skipped - no MT5 account entered. You can "
                  "configure it later from the dashboard Settings page or by "
                  "re-running this script.")
            return 0

    a.setdefault("bridge_port", 8002)
    try:
        validate(a)
    except ConfigError as e:
        print(f"[configure_atlas] ERROR: {e}", file=sys.stderr)
        return 1

    token = existing_token(paths) or secrets.token_urlsafe(32)
    cfg = {
        "login": str(a["login"]).strip(),
        "password": str(a["password"]),
        "server": str(a["server"]).strip(),
        "terminal_path": str(a.get("terminal_path", "") or "").strip(),
        "bridge_host": str(a.get("bridge_host", "127.0.0.1") or "127.0.0.1").strip(),
        "bridge_port": int(a.get("bridge_port", 8002)),
        "bridge_token": token,
    }

    be = write_bridge_env(paths, cfg)
    bk = write_backend_env(paths, cfg)
    js = write_dashboard_json(paths, cfg)

    print("")
    if restored:
        print("[configure_atlas] Restored saved MT5 configuration:")
    else:
        print("[configure_atlas] MT5 credentials saved:")
    print("    bridge  .env : " + str(be))
    print("    backend .env : " + str(bk))
    print("    dashboard    : " + str(js))
    print("    login=" + cfg["login"] + "  server=" + cfg["server"]
          + "  port=" + str(cfg["bridge_port"]))
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

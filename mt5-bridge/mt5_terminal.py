"""Discover and resolve paths to MetaTrader 5 terminal64.exe on Windows.

The MetaTrader5 Python API requires an explicit path to terminal64.exe when the
terminal is installed outside default locations (broker-branded folders) or when
the bridge runs as a Windows service (LocalSystem) and cannot rely on the
current user's %APPDATA% alone.

Resolution order (first hit wins):
  1. Explicit MT5_TERMINAL_PATH from config (file or directory)
  2. Path of a *running* terminal64.exe process (attach to live session)
  3. origin.txt under each user profile's MetaQuotes Terminal data folder
  4. Broker folders under Program Files / Program Files (x86)
  5. Well-known default install paths
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_PATHS = (
    Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"),
)

_SKIP_USER_DIRS = frozenset(
    {"Public", "Default", "Default User", "All Users", "DefaultAppPool"}
)


def normalize_terminal_path(path: str | Path) -> str:
    """Return an absolute forward-slash path suitable for mt5.initialize(path=...)."""
    p = Path(str(path).strip().strip('"'))
    if p.is_dir():
        p = p / "terminal64.exe"
    return str(p.resolve()).replace("\\", "/")


def _add_candidate(found: list[str], seen: set[str], path: str | Path) -> None:
    try:
        norm = normalize_terminal_path(path)
    except (OSError, ValueError):
        return
    p = Path(norm.replace("/", "\\"))
    if p.is_file() and norm not in seen:
        seen.add(norm)
        found.append(norm)


def discover_running_terminal() -> str | None:
    """Return the executable path of a running terminal64.exe, if any."""
    if os.name != "nt":
        return None
    # PowerShell sees terminal processes in every interactive session.
    ps = (
        "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | "
        "Select-Object -First 1 -ExpandProperty Path)"
    )
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            timeout=12,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out and Path(out).is_file():
            return normalize_terminal_path(out)
    except Exception as exc:  # noqa: BLE001
        logger.debug("running-terminal discovery failed: %s", exc)
    return None


def _discover_from_origin_files(found: list[str], seen: set[str]) -> None:
    if os.name != "nt":
        return
    roots: list[Path] = []
    users = Path(r"C:\Users")
    if users.is_dir():
        for profile in users.iterdir():
            if not profile.is_dir() or profile.name in _SKIP_USER_DIRS:
                continue
            roots.append(profile / "AppData" / "Roaming" / "MetaQuotes" / "Terminal")
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        roots.append(Path(appdata) / "MetaQuotes" / "Terminal")

    for root in roots:
        if not root.is_dir():
            continue
        for instance in root.iterdir():
            if not instance.is_dir():
                continue
            origin = instance / "origin.txt"
            if not origin.is_file():
                continue
            try:
                line = origin.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
            if line:
                _add_candidate(found, seen, line)


def _discover_from_program_files(found: list[str], seen: set[str]) -> None:
    if os.name != "nt":
        return
    for base in (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")):
        if not base.is_dir():
            continue
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                _add_candidate(found, seen, child / "terminal64.exe")


def discover_terminal_executables() -> list[str]:
    """Return candidate terminal64.exe paths, best-first."""
    found: list[str] = []
    seen: set[str] = set()

    running = discover_running_terminal()
    if running:
        _add_candidate(found, seen, running)

    for default in _DEFAULT_PATHS:
        _add_candidate(found, seen, default)

    _discover_from_origin_files(found, seen)
    _discover_from_program_files(found, seen)
    return found


def _path_exists(norm: str) -> bool:
    return Path(norm).is_file()


def resolve_terminal_path(configured: str | None) -> tuple[str | None, list[str]]:
    """Resolve the terminal path to pass to mt5.initialize().

    Returns (best_path, ordered_candidates). best_path is None when nothing
    valid was found.
    """
    configured = (configured or "").strip()
    candidates: list[str] = []

    if configured:
        try:
            norm = normalize_terminal_path(configured)
            candidates.append(norm)
            if _path_exists(norm):
                return norm, candidates
        except (OSError, ValueError):
            candidates.append(configured.replace("\\", "/"))

    for cand in discover_terminal_executables():
        if cand not in candidates:
            candidates.append(cand)

    for cand in candidates:
        if _path_exists(cand):
            return cand, candidates
    return None, candidates

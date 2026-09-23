"""Architectural guard: Stage 2a stays isolated and one-way."""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MODULE_ROOT.parents[1]
PACKAGE_ROOT = MODULE_ROOT.parent

FORBIDDEN_PREFIXES = (
    "backend",
    "phase3_knowledge_engine",
    "education",
    "ai_usage",
    "openai",
    "anthropic",
    "MetaTrader5",
)


def _iter_production_py() -> list[Path]:
    return [
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "tests" not in path.parts
    ]


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _top_level_imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_notifications_production_code_does_not_import_phase2_ai_or_knowledge():
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _imported_names(path):
            for prefix in FORBIDDEN_PREFIXES:
                if name == prefix or name.startswith(prefix + "."):
                    offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


def test_no_top_level_network_client_import_in_notifications():
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _top_level_imported_names(path):
            if name in {"httpx", "requests", "aiohttp", "urllib3"} or name.startswith(
                ("httpx.", "requests.", "aiohttp.")
            ):
                offenders.append(f"{path.relative_to(REPO_ROOT)} top-level imports {name}")
    assert offenders == []


def test_no_hardcoded_telegram_token_literals():
    offenders: list[str] = []
    for path in _iter_production_py():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "TELEGRAM_BOT_TOKEN" in stripped and "=" in stripped and "os.environ" not in stripped:
                if stripped.startswith("TELEGRAM_BOT_TOKEN"):
                    offenders.append(f"{path}:{line_no}")
            if "bot" in stripped.lower() and ":" in stripped and stripped.split(":")[0].strip().isdigit():
                offenders.append(f"{path}:{line_no}")
    assert offenders == []


def test_phase2_server_still_does_not_import_notifications_or_telegram():
    server = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    assert "notifications" not in server
    assert "TelegramAdapter" not in server
    assert "FakeTelegramClient" not in server
    assert "TELEGRAM_BOT_TOKEN" not in server

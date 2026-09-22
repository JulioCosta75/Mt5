"""Architectural guard: no network, no LLM SDK, no Phase 2/3/license import."""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MODULE_ROOT.parent

FORBIDDEN_PREFIXES = (
    "backend",
    "phase3_knowledge_engine",
    "notifications",
    "education",
    "httpx",
    "requests",
    "urllib",
    "urllib3",
    "aiohttp",
    "http.client",
    "socket",
    "ssl",
    "openai",
    "anthropic",
)

FORBIDDEN_MODULES = (
    "mt5_client",
    "mt5_adapter",
    "MetaTrader5",
    "license",
)

FORBIDDEN_SUBSTRINGS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "api.anthropic.com",
    "api.openai.com",
)


def _iter_production_py() -> list[Path]:
    return [
        path
        for path in MODULE_ROOT.rglob("*.py")
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


def _is_forbidden(name: str) -> bool:
    if name in FORBIDDEN_MODULES:
        return True
    for prefix in FORBIDDEN_PREFIXES:
        if name == prefix or name.startswith(prefix + "."):
            return True
    return False


def test_ai_usage_has_zero_network_or_cross_module_imports():
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _imported_names(path):
            if _is_forbidden(name):
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


def test_production_code_does_not_mention_provider_credentials():
    offenders: list[str] = []
    for path in _iter_production_py():
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_SUBSTRINGS:
            if needle in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {needle}")
    assert offenders == []


def test_phase2_server_does_not_mention_ai_usage():
    server = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    assert "ai_usage" not in server
    assert "check_quota" not in server
    assert "check_global_budget" not in server

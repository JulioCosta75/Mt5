"""Architectural guard: education/ is fully standalone."""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MODULE_ROOT.parent

FORBIDDEN_PREFIXES = (
    "backend",
    "phase3_knowledge_engine",
    "notifications",
)

FORBIDDEN_MODULES = (
    "mt5_client",
    "mt5_adapter",
    "MetaTrader5",
    "openai",
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


def test_education_has_zero_imports_from_backend_phase3_or_notifications():
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _imported_names(path):
            if _is_forbidden(name):
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


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


def test_anthropic_sdk_is_never_imported_at_module_top_level():
    """Stage 2 may lazy-import anthropic inside a method, never at import time."""
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _top_level_imported_names(path):
            if name == "anthropic" or name.startswith("anthropic."):
                offenders.append(f"{path.relative_to(REPO_ROOT)} top-level imports {name}")
    assert offenders == []


def test_phase2_server_does_not_mention_education():
    server = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    assert "education" not in server
    assert "get_explanation" not in server

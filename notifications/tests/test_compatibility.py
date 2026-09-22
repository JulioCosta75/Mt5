"""Architectural guard: notifications/ must not import Phase 2 execution paths."""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MODULE_ROOT.parent

FORBIDDEN_MODULES = (
    "mt5_client",
    "mt5_adapter",
    "backend.mt5_client",
    "backend.mt5_adapter",
    "backend.routes_mt5",
    "backend.server",
    "server",
    "MetaTrader5",
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


def test_notifications_has_zero_mt5_or_backend_execution_imports():
    offenders: list[str] = []
    for path in _iter_production_py():
        imported = _imported_names(path)
        for name in imported:
            if name in FORBIDDEN_MODULES or name.startswith("backend."):
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


def test_phase2_server_does_not_import_notifications():
    server = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    assert "notifications" not in server
    assert "ATLAS_NOTIFICATIONS_ENABLED" not in server

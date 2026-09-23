"""Architectural guard for education/ai: no Phase 2/3, no network except nested anthropic."""

from __future__ import annotations

import ast
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MODULE_ROOT.parents[1]

FORBIDDEN_PREFIXES = (
    "backend",
    "phase3_knowledge_engine",
    "notifications",
    "httpx",
    "requests",
    "urllib",
    "aiohttp",
    "openai",
)


def _iter_production_py() -> list[Path]:
    return [path for path in MODULE_ROOT.rglob("*.py") if "tests" not in path.parts]


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


def test_ai_package_does_not_import_phase2_or_network_sdks():
    offenders: list[str] = []
    for path in _iter_production_py():
        for name in _imported_names(path):
            if name == "anthropic" or name.startswith("anthropic."):
                continue
            for prefix in FORBIDDEN_PREFIXES:
                if name == prefix or name.startswith(prefix + "."):
                    offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


def test_no_hardcoded_api_key_literals():
    offenders: list[str] = []
    for path in _iter_production_py():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "sk-ant-" in stripped or "sk-live-" in stripped:
                offenders.append(f"{path}:{line_no}")
            if "ANTHROPIC_API_KEY" in stripped and "=" in stripped and "os.environ" not in stripped:
                if stripped.startswith("ANTHROPIC_API_KEY") and "environ" not in stripped:
                    offenders.append(f"{path}:{line_no}")
    assert offenders == []


def test_server_still_does_not_mention_education_ai():
    server = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    assert "education.ai" not in server
    assert "answer_educador_question" not in server
    assert "FakeLLMClient" not in server

"""Anthropic SDK is lazy-imported; the module loads without it installed."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

CLIENTS_PATH = Path(__file__).resolve().parents[1] / "clients.py"


def test_education_ai_clients_imports_without_anthropic_installed():
    sys.modules.pop("anthropic", None)
    sys.modules.pop("education.ai.clients", None)
    sys.modules.pop("education.ai", None)
    module = importlib.import_module("education.ai.clients")
    assert "anthropic" not in sys.modules
    assert hasattr(module, "FakeLLMClient")
    assert hasattr(module, "AnthropicLLMClient")


def test_anthropic_import_is_inside_generate_not_module_body():
    tree = ast.parse(CLIENTS_PATH.read_text(encoding="utf-8"))
    top_level = []
    nested_in_generate = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "anthropic" or alias.name.startswith("anthropic."):
                    top_level.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "anthropic" or node.module.startswith("anthropic."):
                top_level.append(node.module)

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AnthropicLLMClient":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "generate":
                    for child in ast.walk(item):
                        if isinstance(child, ast.Import):
                            for alias in child.names:
                                if alias.name == "anthropic":
                                    nested_in_generate.append(alias.name)
                        elif isinstance(child, ast.ImportFrom) and child.module == "anthropic":
                            nested_in_generate.append(child.module)

    assert top_level == []
    assert nested_in_generate == ["anthropic"]

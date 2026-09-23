"""httpx/requests are lazy-imported; the module loads without them."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

CLIENTS_PATH = Path(__file__).resolve().parents[1] / "clients.py"
NETWORK_MODULES = ("httpx", "requests")


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


def test_telegram_clients_imports_without_httpx_installed():
    sys.modules.pop("httpx", None)
    sys.modules.pop("requests", None)
    sys.modules.pop("notifications.telegram.clients", None)
    sys.modules.pop("notifications.telegram", None)
    module = importlib.import_module("notifications.telegram.clients")
    assert "httpx" not in sys.modules
    assert "requests" not in sys.modules
    assert hasattr(module, "FakeTelegramClient")
    assert hasattr(module, "TelegramAdapter")


def test_httpx_and_requests_are_not_imported_at_module_top_level():
    names = _top_level_imported_names(CLIENTS_PATH)
    offenders = [
        name
        for name in names
        if name in NETWORK_MODULES or name.startswith("httpx.") or name.startswith("requests.")
    ]
    assert offenders == []


def test_httpx_import_is_nested_inside_adapter_http_methods():
    tree = ast.parse(CLIENTS_PATH.read_text(encoding="utf-8"))
    nested: list[str] = []
    for node in tree.body:
        if not (isinstance(node, ast.ClassDef) and node.name == "TelegramAdapter"):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name not in {"_post", "_get", "send_message", "get_updates"}:
                continue
            for child in ast.walk(item):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        if alias.name in NETWORK_MODULES:
                            nested.append(f"{item.name}:{alias.name}")
                elif isinstance(child, ast.ImportFrom) and child.module in NETWORK_MODULES:
                    nested.append(f"{item.name}:{child.module}")
    assert any(item.endswith(":httpx") for item in nested)
    assert any(item.startswith("_post:") or item.startswith("send_message:") for item in nested)
    assert any(item.startswith("_get:") or item.startswith("get_updates:") for item in nested)

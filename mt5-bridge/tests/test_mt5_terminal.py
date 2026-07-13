"""Unit tests for MT5 terminal path discovery (no MetaTrader5 import required)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BRIDGE_DIR = Path(__file__).resolve().parent.parent
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

from mt5_terminal import discover_terminal_executables, normalize_terminal_path, resolve_terminal_path


class TestNormalizeTerminalPath:
    def test_file_path_uses_forward_slashes(self, tmp_path):
        exe = tmp_path / "terminal64.exe"
        exe.write_text("stub", encoding="utf-8")
        norm = normalize_terminal_path(exe)
        assert "/" in norm
        assert norm.endswith("terminal64.exe")

    def test_directory_appends_terminal64(self, tmp_path):
        exe = tmp_path / "terminal64.exe"
        exe.write_text("stub", encoding="utf-8")
        norm = normalize_terminal_path(tmp_path)
        assert norm.endswith("/terminal64.exe")


class TestResolveTerminalPath:
    def test_explicit_missing_file_still_lists_candidates(self, tmp_path):
        missing = tmp_path / "nope" / "terminal64.exe"
        path, candidates = resolve_terminal_path(str(missing))
        assert path is None
        assert candidates

    def test_explicit_valid_file_wins(self, tmp_path):
        exe = tmp_path / "terminal64.exe"
        exe.write_text("stub", encoding="utf-8")
        path, candidates = resolve_terminal_path(str(exe))
        assert path is not None
        assert path.endswith("terminal64.exe")
        assert candidates[0] == path

    def test_discover_on_linux_returns_list(self):
        # No Windows paths on Linux CI — should not raise.
        found = discover_terminal_executables()
        assert isinstance(found, list)

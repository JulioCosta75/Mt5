"""Terminal path must point to the MT5 terminal, not MetaEditor or a folder."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import mt5_config  # noqa: E402

BASE = {"login": "12345678", "password": "pw", "server": "Broker-Demo", "bridge_port": 8002}


@pytest.mark.parametrize(
    "path",
    [
        "",
        "   ",
        r"C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\TERMINAL64.EXE",
        r'"C:\Program Files\MetaTrader 5\terminal64.exe"',
        r"D:\MT5\terminal.exe",
    ],
)
def test_accepts_terminal_or_empty(path):
    mt5_config.validate({**BASE, "terminal_path": path})


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Program Files\Pepperstone MetaTrader 5\MetaEditor64.exe",
        r"C:\Program Files\MetaTrader 5\metatester64.exe",
        "C:\\Program Files\\MetaTrader 5\\",
        r"C:\Program Files\MetaTrader 5",
    ],
)
def test_rejects_other_executables_and_folders(path):
    with pytest.raises(mt5_config.ConfigError, match="terminal64.exe"):
        mt5_config.validate({**BASE, "terminal_path": path})

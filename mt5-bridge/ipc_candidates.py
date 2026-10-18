"""Opt-in experiments for a fresh terminal that returns IPC -10005.

ATLAS_IPC_CANDIDATE empty (the default) leaves initialize() unchanged.
The only candidate that touches disk is servers-dat, and it copies one
file named servers.dat. It does not read or write credentials.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

SERVERS_DAT = "servers.dat"
USER_STEPS = {"broker-terminal", "open-account"}


def selected() -> str:
    return os.environ.get("ATLAS_IPC_CANDIDATE", "").strip().lower()


def prepare_initialize() -> dict:
    """Extra keyword arguments for mt5.initialize.

    servers-dat copies the operator-supplied servers.dat into the fresh
    data directory and requests a portable launch (Eduard Xue, MQL5
    forum 443248, 2026-02-19). broker-terminal and open-account are user
    steps: they change nothing here.
    """
    mode = selected()
    if not mode:
        return {}
    if mode == "servers-dat":
        _copy_servers_dat()
        return {"portable": True}
    if mode in USER_STEPS:
        return {}
    raise ValueError(
        "ATLAS_IPC_CANDIDATE must be servers-dat, broker-terminal, or open-account"
    )


def _copy_servers_dat() -> Path:
    source = os.environ.get("ATLAS_MT5_SERVERS_DAT", "").strip()
    data_dir = os.environ.get("ATLAS_MT5_DATA_DIR", "").strip()
    if not source or not data_dir:
        raise ValueError(
            "servers-dat needs ATLAS_MT5_SERVERS_DAT and ATLAS_MT5_DATA_DIR"
        )
    src = Path(source)
    if src.name.lower() != SERVERS_DAT:
        raise ValueError("ATLAS_MT5_SERVERS_DAT must be a file named servers.dat")
    if not src.is_file():
        raise ValueError("ATLAS_MT5_SERVERS_DAT is not a file")
    dest = Path(data_dir) / "config" / SERVERS_DAT
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return dest

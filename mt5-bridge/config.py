"""Configuration for the MT5 bridge (Windows side).

Loads MT5 credentials and bridge settings from .env. Designed to be portable —
the same code can run with one or more MT5 accounts (one process per account)
by changing the BRIDGE_PORT and MT5_* variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    # MT5 connection
    mt5_login: int
    mt5_password: str
    mt5_server: str
    mt5_terminal_path: str | None  # optional explicit path to terminal64.exe

    # Bridge HTTP
    bridge_host: str
    bridge_port: int
    bridge_token: str

    # Snapshot recorder
    snapshot_interval_seconds: int
    sqlite_path: str

    # Logging
    log_level: str

    @classmethod
    def load(cls) -> "Settings":
        login_raw = os.environ.get("MT5_LOGIN", "").strip()
        if not login_raw:
            raise RuntimeError(
                "MT5_LOGIN not set. Copy .env.example to .env and fill in your "
                "MT5 broker credentials before starting the bridge."
            )
        return cls(
            mt5_login=int(login_raw),
            mt5_password=os.environ["MT5_PASSWORD"],
            mt5_server=os.environ["MT5_SERVER"],
            mt5_terminal_path=os.environ.get("MT5_TERMINAL_PATH") or None,
            bridge_host=os.environ.get("BRIDGE_HOST", "0.0.0.0"),
            bridge_port=int(os.environ.get("BRIDGE_PORT", "8002")),
            bridge_token=os.environ.get("BRIDGE_TOKEN", "").strip()
            or _raise("BRIDGE_TOKEN not set. Generate one with "
                     "`python -c \"import secrets;print(secrets.token_urlsafe(32))\"`"),
            snapshot_interval_seconds=int(os.environ.get("SNAPSHOT_INTERVAL_SECONDS", "10")),
            sqlite_path=os.environ.get("SQLITE_PATH", str(ROOT / "bridge_data.db")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


def _raise(msg: str):
    raise RuntimeError(msg)


settings = Settings.load() if os.environ.get("MT5_LOGIN") else None  # lazy

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
    # Whether a usable MT5 account is configured. When False the bridge still
    # starts and serves /health (reporting "unconfigured") so it never crashes.
    configured: bool

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
        """Load settings, never raising for missing MT5 credentials.

        A missing/invalid MT5_LOGIN simply yields an *unconfigured* Settings so
        the bridge can boot and report its status. The bridge picks up real
        credentials automatically once the .env is written (installer/dashboard)
        and the service is restarted.
        """
        login_raw = os.environ.get("MT5_LOGIN", "").strip()
        configured = login_raw.isdigit() and int(login_raw) > 0

        return cls(
            configured=bool(configured),
            mt5_login=int(login_raw) if configured else 0,
            mt5_password=os.environ.get("MT5_PASSWORD", ""),
            mt5_server=os.environ.get("MT5_SERVER", ""),
            mt5_terminal_path=os.environ.get("MT5_TERMINAL_PATH") or None,
            bridge_host=os.environ.get("BRIDGE_HOST", "0.0.0.0"),
            bridge_port=int(os.environ.get("BRIDGE_PORT", "8002")),
            # A token is optional while unconfigured (no data is served). Once
            # configured the installer/dashboard always writes a strong token.
            bridge_token=os.environ.get("BRIDGE_TOKEN", "").strip(),
            snapshot_interval_seconds=int(os.environ.get("SNAPSHOT_INTERVAL_SECONDS", "10")),
            sqlite_path=os.environ.get("SQLITE_PATH", str(ROOT / "bridge_data.db")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


settings = Settings.load()

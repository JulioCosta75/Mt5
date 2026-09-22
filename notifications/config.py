"""Notifications configuration — isolated from Phase 2 backend settings."""

from __future__ import annotations

import os

# Future-proofing only. Stage 1 does not touch backend/server.py.
ATLAS_NOTIFICATIONS_ENABLED: bool = (
    os.environ.get("ATLAS_NOTIFICATIONS_ENABLED", "false").lower() in ("1", "true", "yes")
)

DEFAULT_NOTIFICATIONS_DB_PATH: str = os.environ.get(
    "ATLAS_NOTIFICATIONS_DB_PATH", "notifications.db"
)

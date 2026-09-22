"""Shared frozen clock for synthetic usage tests."""

from __future__ import annotations

from datetime import datetime, timezone

FIXED_NOW = datetime(2026, 9, 22, 15, 0, 0, tzinfo=timezone.utc)

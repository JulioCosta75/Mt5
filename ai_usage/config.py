"""AI usage configuration — isolated from Phase 2 backend settings.

Pricing and quota ceilings live in JSON files next to this module so rates
can be updated without a code change. Override paths with
``ATLAS_AI_USAGE_PRICING_PATH`` and ``ATLAS_AI_USAGE_QUOTAS_PATH``.
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent

DEFAULT_AI_USAGE_DB_PATH: str = os.environ.get("ATLAS_AI_USAGE_DB_PATH", "ai_usage.db")

DEFAULT_PRICING_PATH: str = os.environ.get(
    "ATLAS_AI_USAGE_PRICING_PATH",
    str(_PACKAGE_DIR / "pricing.json"),
)

DEFAULT_QUOTAS_PATH: str = os.environ.get(
    "ATLAS_AI_USAGE_QUOTAS_PATH",
    str(_PACKAGE_DIR / "quotas.json"),
)

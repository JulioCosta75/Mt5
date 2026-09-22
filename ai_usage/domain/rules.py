"""Validation, pricing, and fail-closed quota helpers."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from ai_usage.domain.entities import (
    LICENSE_TIER_ALIASES,
    MODELS,
    MODES,
    TIERS,
)

_COST_QUANTUM = Decimal("0.00000001")
_MILLION = Decimal("1000000")


class UsageValidationError(ValueError):
    """Raised when a usage field is invalid. Never silently accepted."""


def require_user_id(user_id: str) -> str:
    raw = (user_id or "").strip()
    if not raw:
        raise UsageValidationError("user_id is required.")
    return raw


def require_mode(mode: str) -> str:
    raw = (mode or "").strip().lower()
    if raw not in MODES:
        allowed = ", ".join(sorted(MODES))
        raise UsageValidationError(f"unknown mode {mode!r}; allowed: {allowed}.")
    return raw


def require_model(model: str) -> str:
    raw = (model or "").strip().lower()
    if raw not in MODELS:
        allowed = ", ".join(sorted(MODELS))
        raise UsageValidationError(f"unknown model {model!r}; allowed: {allowed}.")
    return raw


def require_token_count(value: int, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise UsageValidationError(f"{field} must be a non-negative integer.")
    return value


def normalize_tier(tier: str) -> str | None:
    """Map a license-style status onto free/pro, or None if unknown (fail closed)."""
    raw = (tier or "").strip().lower()
    mapped = LICENSE_TIER_ALIASES.get(raw)
    if mapped in TIERS:
        return mapped
    return None


def load_json_object(path: str | Path) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise UsageValidationError(f"{path} must be a JSON object.")
    return raw


def load_pricing(path: str) -> dict:
    data = load_json_object(path)
    for model in MODELS:
        if model not in data:
            raise UsageValidationError(f"pricing.json missing model {model!r}.")
        row = data[model]
        if not isinstance(row, dict):
            raise UsageValidationError(f"pricing.json {model!r} must be an object.")
        for key in ("input_usd_per_million", "output_usd_per_million"):
            if key not in row:
                raise UsageValidationError(f"pricing.json {model!r} missing {key}.")
    return data


def load_quotas(path: str) -> dict:
    data = load_json_object(path)
    if "tiers" not in data or "global" not in data or "rate_limit" not in data:
        raise UsageValidationError("quotas.json must include tiers, global, and rate_limit.")
    return data


def estimate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict,
) -> Decimal:
    rates = pricing[model]
    cost = (
        Decimal(input_tokens) / _MILLION * Decimal(str(rates["input_usd_per_million"]))
        + Decimal(output_tokens) / _MILLION * Decimal(str(rates["output_usd_per_million"]))
    )
    return cost.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)


def decimal_limit(value) -> Decimal:
    return Decimal(str(value))

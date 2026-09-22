"""Haiku and Sonnet estimated costs from the JSON pricing table."""

from __future__ import annotations

from decimal import Decimal

from ai_usage.config import DEFAULT_PRICING_PATH
from ai_usage.domain.rules import estimate_cost_usd, load_pricing
from ai_usage.tests.clock import FIXED_NOW


def test_pricing_table_matches_founder_rates():
    pricing = load_pricing(DEFAULT_PRICING_PATH)
    assert pricing["haiku"]["input_usd_per_million"] == 1.0
    assert pricing["haiku"]["output_usd_per_million"] == 5.0
    assert pricing["sonnet"]["input_usd_per_million"] == 2.0
    assert pricing["sonnet"]["output_usd_per_million"] == 10.0


def test_haiku_cost_per_million_tokens():
    pricing = load_pricing(DEFAULT_PRICING_PATH)
    assert estimate_cost_usd("haiku", 1_000_000, 0, pricing) == Decimal("1.00000000")
    assert estimate_cost_usd("haiku", 0, 1_000_000, pricing) == Decimal("5.00000000")


def test_sonnet_cost_per_million_tokens():
    pricing = load_pricing(DEFAULT_PRICING_PATH)
    assert estimate_cost_usd("sonnet", 1_000_000, 0, pricing) == Decimal("2.00000000")
    assert estimate_cost_usd("sonnet", 0, 1_000_000, pricing) == Decimal("10.00000000")


def test_mixed_token_cost_and_record_usage_computes_it(tmp_svc):
    pricing = load_pricing(DEFAULT_PRICING_PATH)
    expected = estimate_cost_usd("haiku", 1000, 500, pricing)
    assert expected == Decimal("0.00350000")
    svc = tmp_svc()
    record = svc.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=1000,
        output_tokens=500,
        occurred_at=FIXED_NOW,
    )
    assert record.estimated_cost_usd == expected


def test_pricing_override_file_changes_cost_without_code_change(tmp_svc, tmp_path):
    import json

    override = tmp_path / "pricing.json"
    override.write_text(
        json.dumps(
            {
                "haiku": {"input_usd_per_million": 10.0, "output_usd_per_million": 20.0},
                "sonnet": {"input_usd_per_million": 2.0, "output_usd_per_million": 10.0},
            }
        ),
        encoding="utf-8",
    )
    svc = tmp_svc(pricing_path=str(override))
    record = svc.record_usage(
        user_id="alice",
        mode="educador",
        model="haiku",
        input_tokens=1_000_000,
        output_tokens=0,
        occurred_at=FIXED_NOW,
    )
    assert record.estimated_cost_usd == Decimal("10.00000000")

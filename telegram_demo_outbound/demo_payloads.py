"""Deterministic synthetic payloads for the SUS-010 DEMO outbound delivery."""

from telegram_demo_outbound.events import (
    DailySummaryEvent,
    OrderCreatedEvent,
    StartupEvent,
    format_daily_summary,
    format_order_created,
    format_startup,
)

SYNTHETIC_STARTUP = StartupEvent(
    component="telegram_demo_outbound",
    started_at="2026-09-01T00:00:00Z",
    app_mode="demo",
    synthetic=True,
)

SYNTHETIC_ORDER_CREATED = OrderCreatedEvent(
    account="SYNTHETIC-DEMO-0001",
    account_mode="demo",
    strategy="SYNTHETIC_STRATEGY",
    strategy_version="0.0.0-synthetic",
    symbol="SYN-EURUSD",
    direction="buy",
    quantity="0.10",
    price="1.08500",
    notional_value="10850.00",
    commission="0.70",
    stop="1.08000",
    target="1.09500",
    risk_money="50.00",
    risk_percent="0.50",
    synthetic=True,
)

SYNTHETIC_DAILY_SUMMARY = DailySummaryEvent(
    balance="10000.00",
    equity="10025.50",
    drawdown="120.00",
    exposure="21700.00",
    costs="2.10",
    period="synthetic-day-2026-09-01",
    synthetic=True,
)


def startup_text() -> str:
    return format_startup(SYNTHETIC_STARTUP)


def order_created_text() -> str:
    return format_order_created(SYNTHETIC_ORDER_CREATED)


def daily_summary_text() -> str:
    return format_daily_summary(SYNTHETIC_DAILY_SUMMARY)

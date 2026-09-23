"""Synthetic DEMO event payloads. Not connected to any trading account."""

from __future__ import annotations

from dataclasses import dataclass

from telegram_demo_outbound.constants import REQUIRED_PREFIX, SYNTHETIC_BANNER

ORDER_CREATED_FIELDS = (
    "account",
    "account_mode",
    "strategy",
    "strategy_version",
    "symbol",
    "direction",
    "quantity",
    "price",
    "notional_value",
    "commission",
    "stop",
    "target",
    "risk_money",
    "risk_percent",
)

DAILY_SUMMARY_FIELDS = (
    "balance",
    "equity",
    "drawdown",
    "exposure",
    "costs",
)


@dataclass(frozen=True)
class StartupEvent:
    component: str
    started_at: str
    app_mode: str
    synthetic: bool = True


@dataclass(frozen=True)
class OrderCreatedEvent:
    account: str
    account_mode: str
    strategy: str
    strategy_version: str
    symbol: str
    direction: str
    quantity: str
    price: str
    notional_value: str
    commission: str
    stop: str
    target: str
    risk_money: str
    risk_percent: str
    synthetic: bool = True


@dataclass(frozen=True)
class DailySummaryEvent:
    balance: str
    equity: str
    drawdown: str
    exposure: str
    costs: str
    period: str = "synthetic-day"
    synthetic: bool = True


def ensure_prefix(text: str) -> str:
    if text.startswith(REQUIRED_PREFIX):
        return text
    if text == "":
        return REQUIRED_PREFIX
    return f"{REQUIRED_PREFIX}\n{text}"


def _header(event_name: str, synthetic: bool) -> list[str]:
    lines = [REQUIRED_PREFIX]
    if synthetic:
        lines.append(SYNTHETIC_BANNER)
    lines.append("")
    lines.append(f"event: {event_name}")
    return lines


def format_startup(event: StartupEvent) -> str:
    lines = _header("startup", event.synthetic)
    lines.extend(
        [
            f"component: {event.component}",
            f"started_at: {event.started_at}",
            f"app_mode: {event.app_mode}",
            f"synthetic: {str(event.synthetic).lower()}",
        ]
    )
    return "\n".join(lines)


def format_order_created(event: OrderCreatedEvent) -> str:
    lines = _header("order_created", event.synthetic)
    lines.extend(
        [
            f"account: {event.account}",
            f"account_mode: {event.account_mode}",
            f"strategy: {event.strategy}",
            f"strategy_version: {event.strategy_version}",
            f"symbol: {event.symbol}",
            f"direction: {event.direction}",
            f"quantity: {event.quantity}",
            f"price: {event.price}",
            f"notional_value: {event.notional_value}",
            f"commission: {event.commission}",
            f"stop: {event.stop}",
            f"target: {event.target}",
            f"risk_money: {event.risk_money}",
            f"risk_percent: {event.risk_percent}",
            f"synthetic: {str(event.synthetic).lower()}",
        ]
    )
    return "\n".join(lines)


def format_daily_summary(event: DailySummaryEvent) -> str:
    lines = _header("daily_summary", event.synthetic)
    lines.extend(
        [
            f"period: {event.period}",
            f"balance: {event.balance}",
            f"equity: {event.equity}",
            f"drawdown: {event.drawdown}",
            f"exposure: {event.exposure}",
            f"costs: {event.costs}",
            f"synthetic: {str(event.synthetic).lower()}",
        ]
    )
    return "\n".join(lines)


def missing_order_fields(text: str) -> list[str]:
    return [name for name in ORDER_CREATED_FIELDS if f"{name}:" not in text]


def missing_summary_fields(text: str) -> list[str]:
    return [name for name in DAILY_SUMMARY_FIELDS if f"{name}:" not in text]

"""Per-account Sr. Atlas report builders (Phase 2).

Pure helpers — no FastAPI / Mongo imports. Used by ``server.py`` to persist
one report per MT5 account (never a cross-account sum).
"""
from __future__ import annotations

from typing import Any


def account_report_status(acc: dict, *, bridge_ok: bool | None) -> str:
    """Per-account OK/WARNING/ALERT — never OK when bridge is down."""
    if acc.get("status") == "ERROR":
        status = "ALERT"
    elif acc.get("status") == "PAUSED":
        status = "WARNING"
    else:
        limits = acc.get("risk_limits") or {}
        max_dd = float(limits.get("max_daily_loss_pct", 5.0))
        if abs(float(acc.get("current_drawdown", 0.0))) >= max_dd:
            status = "WARNING"
        else:
            status = "OK"
    if bridge_ok is False and status == "OK":
        status = "WARNING"
    if acc.get("stale") and status == "OK":
        status = "WARNING"
    return status


def build_account_report(
    acc: dict,
    *,
    source: str,
    bridge_ok: bool | None,
    supervisor: str = "Sr. Atlas",
    ecosystem: str = "Forge Factory Lab",
    message_override: str | None = None,
    status_override: str | None = None,
    backend_ok: bool | None = None,
    dashboard_ok: bool | None = None,
) -> dict[str, Any]:
    """Build one report document for a single account (no secrets)."""
    status = (status_override or account_report_status(acc, bridge_ok=bridge_ok)).upper()
    if acc.get("stale"):
        data_origin = "cache"
    elif bridge_ok:
        data_origin = "live"
    elif bridge_ok is False:
        data_origin = "cache"
    else:
        data_origin = "live"  # mock mode

    if message_override:
        message = message_override
    elif bridge_ok is False:
        message = (
            f"Account {acc.get('login')} — bridge unavailable; "
            "data may be outdated."
        )
    elif acc.get("stale"):
        message = f"Account {acc.get('login')} — cached snapshot (bridge not live)."
    else:
        currency = acc.get("currency") or ""
        message = (
            f"Account {acc.get('login')} — equity {acc.get('equity')} {currency}".strip()
            + f", daily P&L {acc.get('daily_pnl')}, "
            f"positions {acc.get('open_positions')}."
        )

    return {
        "supervisor": supervisor,
        "ecosystem": ecosystem,
        "account_id": acc["id"],
        "login": acc.get("login"),
        "server": acc.get("broker") or acc.get("server"),
        "currency": acc.get("currency"),
        "status": status,
        "backend_ok": True if backend_ok is None else backend_ok,
        "bridge_ok": bridge_ok if bridge_ok is not None else None,
        "dashboard_ok": True if dashboard_ok is None else dashboard_ok,
        "message": message,
        "source": source,
        "data_origin": data_origin,
        "account_status": acc.get("status"),
        "metrics": {
            "equity": acc.get("equity"),
            "balance": acc.get("balance"),
            "daily_pnl": acc.get("daily_pnl"),
            "open_positions": acc.get("open_positions"),
            "current_drawdown": acc.get("current_drawdown"),
            "max_drawdown": acc.get("max_drawdown"),
            "risk_limits": acc.get("risk_limits") or {},
        },
    }

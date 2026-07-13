"""Build the Sr. Atlas supervision snapshot from account + alert feeds.

Mock mode and MT5 mode share this aggregator so the dashboard never mixes
in-memory sample accounts with live bridge data.
"""
from __future__ import annotations

from datetime import datetime, timezone


def build_supervision_snapshot(
    accounts: list[dict],
    alerts: list[dict],
    *,
    mode: str,
    bridge_ok: bool | None,
) -> dict:
    total_equity = sum(float(a.get("equity", 0) or 0) for a in accounts)
    total_balance = sum(float(a.get("balance", 0) or 0) for a in accounts)
    daily_pnl = sum(float(a.get("daily_pnl", 0) or 0) for a in accounts)
    open_positions = sum(int(a.get("open_positions", 0) or 0) for a in accounts)

    live = sum(1 for a in accounts if a.get("status") == "LIVE")
    paused = sum(1 for a in accounts if a.get("status") == "PAUSED")
    error = sum(1 for a in accounts if a.get("status") == "ERROR")

    active_alerts = sum(1 for a in alerts if not a.get("acknowledged"))
    critical = sum(
        1 for a in alerts
        if a.get("severity") == "CRITICAL" and not a.get("acknowledged")
    )
    warning = sum(
        1 for a in alerts
        if a.get("severity") == "WARNING" and not a.get("acknowledged")
    )

    n = max(len(accounts), 1)
    avg_dd = round(sum(float(a.get("current_drawdown", 0) or 0) for a in accounts) / n, 2)
    worst_dd = round(
        min((float(a.get("current_drawdown", 0) or 0) for a in accounts), default=0.0),
        2,
    )
    accounts_over_limit = sum(
        1 for a in accounts
        if abs(float(a.get("current_drawdown", 0) or 0))
        >= float((a.get("risk_limits") or {}).get("max_daily_loss_pct", 100))
    )

    if error > 0 or critical > 0:
        status = "ALERT"
    elif paused > 0 or warning > 0 or accounts_over_limit > 0:
        status = "WARNING"
    else:
        status = "OK"

    services = {
        "backend_ok": True,
        "store_ok": True,
        "bridge_ok": bridge_ok,
        "dashboard_ok": True,
    }

    if mode == "mt5":
        if not accounts:
            message = "MT5 mode — waiting for a connected MetaTrader 5 account."
        elif status == "OK":
            message = (
                f"MT5 live feed: {live} account(s) connected, "
                f"equity {round(total_equity, 2):,.2f}."
            )
        elif status == "WARNING":
            message = (
                f"MT5 live feed degraded: {paused} paused account(s), "
                f"{accounts_over_limit} near risk limits."
            )
        else:
            message = (
                f"MT5 live feed alert: {error} account(s) in ERROR state."
            )
    elif status == "OK":
        message = "All Forge Factory Lab core services are online and healthy."
    elif status == "WARNING":
        message = (
            f"Degraded: {warning} warning alert(s), {paused} paused account(s), "
            f"{accounts_over_limit} account(s) near risk limits."
        )
    else:
        message = f"ALERT: {critical} critical alert(s), {error} account(s) in ERROR state."

    return {
        "supervisor": "Sr. Atlas",
        "ecosystem": "Forge Factory Lab",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": status,
        "kpis": {
            "total_equity": round(total_equity, 2),
            "total_balance": round(total_balance, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl / total_equity * 100, 2) if total_equity else 0.0,
            "open_positions": open_positions,
        },
        "accounts": {"total": len(accounts), "live": live, "paused": paused, "error": error},
        "risk": {
            "avg_drawdown": avg_dd,
            "worst_drawdown": worst_dd,
            "accounts_over_limit": accounts_over_limit,
        },
        "alerts": {"active": active_alerts, "critical": critical, "warning": warning},
        "services": services,
        "message": message,
    }

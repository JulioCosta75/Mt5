"""Adapter: map MT5 bridge payloads into the JSON schema the React frontend
already expects. This is the single source of truth for the contract so the
frontend doesn't need to change.

The frontend reads account objects with these keys:
    id, login, broker, strategy, currency, leverage,
    balance, equity, daily_pnl, max_drawdown, current_drawdown,
    open_positions, margin_used, margin_level, status,
    kill_switch, risk_limits

We map them from the bridge as follows:
    id            <- f"MT5-{login}"
    broker        <- mt5.broker (company) or mt5.server
    strategy      <- "Live MT5" until we group by magic number (Phase 2)
    currency      <- mt5.currency
    leverage      <- mt5.leverage
    balance/equity/margin -> direct
    daily_pnl     <- mt5.profit (running floating P&L of open positions today;
                                 refined in Phase 1.1 with daily anchor)
    status        <- LIVE / PAUSED / ERROR based on connected & trade_allowed
    open_positions <- len(positions)
    margin_used    <- mt5.margin
    margin_level   <- equity / margin * 100   (0 if margin == 0)
    risk_limits    <- persisted in Mongo (separate concern)
    kill_switch    <- persisted in Mongo
"""
from __future__ import annotations

from datetime import datetime, timezone


# ---- account ----
def account_from_bridge(bridge_account: dict, positions_count: int,
                        risk_limits: dict, kill_switch: bool,
                        max_dd: float = 0.0, current_dd: float = 0.0,
                        daily_pnl_anchor: float | None = None) -> dict:
    equity = float(bridge_account.get("equity", 0.0))
    balance = float(bridge_account.get("balance", 0.0))
    margin = float(bridge_account.get("margin", 0.0))
    margin_level = (equity / margin * 100.0) if margin else 0.0

    connected = bool(bridge_account.get("connected"))
    trade_allowed = bool(bridge_account.get("trade_allowed"))
    if kill_switch:
        status = "PAUSED"
    elif not connected:
        status = "ERROR"
    elif not trade_allowed:
        status = "PAUSED"
    else:
        status = "LIVE"

    # daily_pnl: prefer (equity - daily_anchor_balance) if we have it, else use
    # MT5's running profit on open positions as a proxy.
    if daily_pnl_anchor is not None:
        daily_pnl = round(equity - daily_pnl_anchor, 2)
    else:
        daily_pnl = round(float(bridge_account.get("profit", 0.0)), 2)

    login = int(bridge_account["login"])
    return {
        "id": f"MT5-{login}",
        "login": login,
        "name": bridge_account.get("name", ""),
        "broker": bridge_account.get("broker") or bridge_account.get("server", ""),
        "strategy": "Live MT5",
        "currency": bridge_account.get("currency", "USD"),
        "leverage": int(bridge_account.get("leverage", 0)),
        "balance": round(balance, 2),
        "equity": round(equity, 2),
        "daily_pnl": daily_pnl,
        "max_drawdown": round(max_dd, 2),
        "current_drawdown": round(current_dd, 2),
        "open_positions": positions_count,
        "margin_used": round(margin, 2),
        "margin_level": round(margin_level, 1),
        "status": status,
        "kill_switch": kill_switch,
        "risk_limits": risk_limits,
        # extras (frontend ignores unknown keys)
        "margin_free": round(float(bridge_account.get("margin_free", 0.0)), 2),
        "connected": connected,
        "trade_allowed": trade_allowed,
        "source": "mt5",
    }


# ---- equity / drawdown ----
def drawdown_from_equity(series: list[dict]) -> tuple[list[dict], float, float]:
    """Return (drawdown_series, max_dd_pct, current_dd_pct)."""
    if not series:
        return [], 0.0, 0.0
    peak = float("-inf")
    out = []
    max_dd = 0.0
    for p in series:
        eq = float(p["equity"])
        peak = max(peak, eq)
        dd = (eq - peak) / peak * 100.0 if peak > 0 else 0.0
        max_dd = min(max_dd, dd)
        out.append({"t": p["t"], "dd": round(dd, 3)})
    last_eq = float(series[-1]["equity"])
    current_dd = round((last_eq - peak) / peak * 100.0, 2) if peak > 0 else 0.0
    return out, round(max_dd, 2), current_dd


# ---- trades ----
def trades_from_deals(deals: list[dict]) -> list[dict]:
    """Map MT5 deals into the frontend trade-row schema.

    MT5 deals are per-leg (entry OR exit). The frontend table treats each
    exit-deal as a closed trade. We approximate by:
      - keeping deals with non-zero profit (typically the closing leg);
      - using deal.time as close_time;
      - duration_min computed when possible from matching position_id pairs.

    This is a usable approximation for MVP; a Phase 1.2 task is to do exact
    position-pairing for entry/exit times.
    """
    # group by position_id so we can pair entry+exit
    by_pos: dict[int, list[dict]] = {}
    for d in deals:
        by_pos.setdefault(d.get("position_id", 0), []).append(d)

    rows = []
    for pid, legs in by_pos.items():
        if len(legs) < 2:
            # only entry, still open or skipped
            continue
        legs.sort(key=lambda x: x["time"])
        entry, *_, exit_ = legs
        pnl = sum(float(leg.get("profit", 0)) + float(leg.get("swap", 0)) + float(leg.get("commission", 0)) for leg in legs)
        try:
            t_open = datetime.fromisoformat(entry["time"])
            t_close = datetime.fromisoformat(exit_["time"])
            duration_min = max(1, int((t_close - t_open).total_seconds() / 60))
        except Exception:  # noqa: BLE001
            t_open = t_close = datetime.now(timezone.utc)
            duration_min = 0
        rows.append({
            "id": f"DEAL-{exit_['ticket']}",
            "symbol": exit_["symbol"],
            "side": entry["side"],     # direction of the trade = direction of entry
            "lots": float(entry["volume"]),
            "pnl": round(pnl, 2),
            "open_time": t_open.isoformat(),
            "close_time": t_close.isoformat(),
            "open_price": float(entry["price"]),
            "close_price": float(exit_["price"]),
            "strategy": f"magic-{entry.get('magic', 0)}" if entry.get("magic") else "Live MT5",
            "duration_min": duration_min,
        })
    rows.sort(key=lambda r: r["close_time"], reverse=True)
    return rows


# ---- positions / orders (pass-through, normalised) ----
def positions_passthrough(positions: list[dict]) -> list[dict]:
    return positions


def orders_passthrough(orders: list[dict]) -> list[dict]:
    return orders

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
    strategy      <- "Live MT5" (account-level; EA breakdown is /api/eas)
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

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

COMMENT_CONSISTENCY_THRESHOLD = 0.60
# Absolute money peak below this makes %-drawdown meaningless on a PnL curve.
_MIN_PEAK_FOR_DD_PCT = 10.0
# Clamp absurd percentage drawdowns even when peak clears the floor.
_DD_PCT_FLOOR = -100.0

_JUNK_COMMENT_RE = re.compile(
    r"^(?:"
    r"from\s*#?\d+"
    r"|to\s*#?\d+"
    r"|#[0-9]+"
    r"|\d+"
    r"|\[?\s*(?:sl|tp|stop(?:loss)?|trailing)\b.*"
    r"|(?:sl|tp)\s*[:=]?\s*[\d.].*"
    r")$",
    re.IGNORECASE,
)


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


# ---- EA naming / grouping -------------------------------------------------
def comment_is_usable(comment: object) -> bool:
    """True when an MT5 comment is usable as a friendly EA name."""
    if comment is None:
        return False
    text = str(comment).strip()
    if not text:
        return False
    if _JUNK_COMMENT_RE.match(text):
        return False
    # Reject strings that are mostly digits/punctuation (no real name).
    letters = sum(1 for ch in text if ch.isalpha())
    if letters < 3:
        return False
    return True


def resolve_ea_label(
    magic: int,
    comments: list[object],
    override: str | None = None,
) -> tuple[str, str]:
    """Return (label, source) using the founder-approved naming rule.

    Priority: manual override → consistent comment (≥60%) → ``EA {magic}``
    → magic 0 = ``Manual / sem EA``.
    """
    if override is not None:
        cleaned = str(override).strip()
        if cleaned:
            return cleaned, "manual"

    magic_i = int(magic or 0)
    if magic_i == 0:
        return "Manual / sem EA", "manual_zero"

    usable = [str(c).strip() for c in comments if comment_is_usable(c)]
    if usable:
        top, count = Counter(usable).most_common(1)[0]
        if (count / len(usable)) >= COMMENT_CONSISTENCY_THRESHOLD:
            return top, "comment"

    return f"EA {magic_i}", "fallback"


def _deal_net_pnl(deal: dict) -> float:
    return (
        float(deal.get("profit", 0) or 0)
        + float(deal.get("swap", 0) or 0)
        + float(deal.get("commission", 0) or 0)
    )


def _drawdown_from_pnl_curve(pnls_chrono: list[float]) -> dict:
    """Approximate drawdown from a cumulative realized-PnL curve.

    Returns pct fields only when the equity peak is large enough to be a
    meaningful denominator; otherwise reports money drawdown and zeroes pct
    (avoids nonsense like -1473%).
    """
    empty = {
        "max_drawdown": 0.0,
        "current_drawdown": 0.0,
        "max_drawdown_money": 0.0,
        "current_drawdown_money": 0.0,
        "drawdown_unit": "pct",
    }
    if not pnls_chrono:
        return empty

    equity = 0.0
    peak = 0.0
    max_dd_pct = 0.0
    max_dd_money = 0.0
    for pnl in pnls_chrono:
        equity += float(pnl)
        peak = max(peak, equity)
        drop_money = peak - equity
        if drop_money > max_dd_money:
            max_dd_money = drop_money
        if peak >= _MIN_PEAK_FOR_DD_PCT:
            dd = (equity - peak) / peak * 100.0
            max_dd_pct = min(max_dd_pct, dd)

    current_money = max(0.0, peak - equity)
    if peak >= _MIN_PEAK_FOR_DD_PCT:
        current_pct = (equity - peak) / peak * 100.0
        return {
            "max_drawdown": round(max(max_dd_pct, _DD_PCT_FLOOR), 2),
            "current_drawdown": round(max(current_pct, _DD_PCT_FLOOR), 2),
            "max_drawdown_money": round(max_dd_money, 2),
            "current_drawdown_money": round(current_money, 2),
            "drawdown_unit": "pct",
        }

    return {
        "max_drawdown": 0.0,
        "current_drawdown": 0.0,
        "max_drawdown_money": round(max_dd_money, 2),
        "current_drawdown_money": round(current_money, 2),
        "drawdown_unit": "money",
    }


def eas_from_bridge(
    *,
    account_id: str,
    login: int,
    positions: list[dict],
    deals: list[dict],
    label_overrides: dict[int, str] | None = None,
) -> list[dict]:
    """Build per-magic EA rows from live positions + history deals."""
    overrides = {int(k): str(v) for k, v in (label_overrides or {}).items()}

    by_magic_comments: dict[int, list[str]] = defaultdict(list)
    by_magic_pos: dict[int, list[dict]] = defaultdict(list)
    by_magic_deals: dict[int, list[dict]] = defaultdict(list)

    for p in positions or []:
        magic = int(p.get("magic", 0) or 0)
        by_magic_pos[magic].append(p)
        if p.get("comment") is not None:
            by_magic_comments[magic].append(p.get("comment"))

    for d in deals or []:
        magic = int(d.get("magic", 0) or 0)
        by_magic_deals[magic].append(d)
        if d.get("comment") is not None:
            by_magic_comments[magic].append(d.get("comment"))

    magics = sorted(set(by_magic_pos) | set(by_magic_deals) | set(overrides))
    rows: list[dict] = []
    for magic in magics:
        if (
            magic not in by_magic_pos
            and magic not in by_magic_deals
            and magic not in overrides
        ):
            continue

        label, source = resolve_ea_label(
            magic, by_magic_comments.get(magic, []), overrides.get(magic)
        )
        poss = by_magic_pos.get(magic, [])
        deals_m = by_magic_deals.get(magic, [])
        floating = sum(
            float(p.get("profit", 0) or 0) + float(p.get("swap", 0) or 0) for p in poss
        )
        closed = trades_from_deals(deals_m, label_overrides=overrides)
        realized = sum(float(t.get("pnl", 0) or 0) for t in closed)
        wins = sum(1 for t in closed if float(t.get("pnl", 0) or 0) > 0)
        win_rate = round((wins / len(closed) * 100.0), 1) if closed else 0.0

        chrono = sorted(deals_m, key=lambda x: x.get("time") or "")
        dd = _drawdown_from_pnl_curve([_deal_net_pnl(d) for d in chrono])

        rows.append({
            "id": f"{account_id}:magic-{magic}",
            "account_id": account_id,
            "login": int(login),
            "magic": magic,
            "label": label,
            "label_source": source,
            "open_positions": len(poss),
            "floating_pnl": round(floating, 2),
            "realized_pnl": round(realized, 2),
            "net_pnl": round(realized + floating, 2),
            "trade_count": len(closed),
            "win_rate": win_rate,
            "max_drawdown": dd["max_drawdown"],
            "current_drawdown": dd["current_drawdown"],
            "max_drawdown_money": dd["max_drawdown_money"],
            "current_drawdown_money": dd["current_drawdown_money"],
            "drawdown_unit": dd["drawdown_unit"],
            "symbols": sorted({str(p.get("symbol")) for p in poss if p.get("symbol")}),
        })

    rows.sort(key=lambda r: (r["open_positions"] == 0, -abs(r["net_pnl"]), r["magic"]))
    return rows


# ---- trades ----
def trades_from_deals(deals: list[dict], label_overrides: dict[int, str] | None = None) -> list[dict]:
    """Map MT5 deals into the frontend trade-row schema.

    MT5 deals are per-leg (entry OR exit). The frontend table treats each
    exit-deal as a closed trade. We approximate by:
      - keeping deals with non-zero profit (typically the closing leg);
      - using deal.time as close_time;
      - duration_min computed when possible from matching position_id pairs.

    This is a usable approximation for MVP; a Phase 1.2 task is to do exact
    position-pairing for entry/exit times.
    """
    overrides = {int(k): str(v) for k, v in (label_overrides or {}).items()}
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
        pnl = sum(_deal_net_pnl(leg) for leg in legs)
        try:
            t_open = datetime.fromisoformat(entry["time"])
            t_close = datetime.fromisoformat(exit_["time"])
            duration_min = max(1, int((t_close - t_open).total_seconds() / 60))
        except Exception:  # noqa: BLE001
            t_open = t_close = datetime.now(timezone.utc)
            duration_min = 0
        magic = int(entry.get("magic", 0) or 0)
        comments = [leg.get("comment") for leg in legs]
        label, _src = resolve_ea_label(magic, comments, overrides.get(magic))
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
            "magic": magic,
            "comment": entry.get("comment") or exit_.get("comment") or "",
            "strategy": label,
            "duration_min": duration_min,
        })
    rows.sort(key=lambda r: r["close_time"], reverse=True)
    return rows


# ---- positions / orders (pass-through, normalised) ----
def positions_passthrough(positions: list[dict]) -> list[dict]:
    return positions


def orders_passthrough(orders: list[dict]) -> list[dict]:
    return orders

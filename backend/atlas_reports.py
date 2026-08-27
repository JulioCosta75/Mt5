"""Per-account Sr. Atlas report builders (Phase 2).

Pure helpers — no FastAPI / Mongo imports. Used by ``server.py`` to persist
one report per MT5 account (never a cross-account sum).

Part 3 enrichment reuses ``eas_from_bridge``, ``trades_from_deals``, and
``positions_passthrough`` from ``mt5_adapter`` — no duplicated mapping logic.
Fields without a real data source (demo/real, session) are omitted or marked
``not_available`` — never invented.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mt5_adapter import eas_from_bridge, positions_passthrough, trades_from_deals


def account_report_status(
    acc: dict,
    *,
    bridge_ok: bool | None,
    open_positions: list[dict] | None = None,
) -> str:
    """Per-account OK/WARNING/ALERT — never OK when bridge is down.

    Limit breaches reuse ``limits_status`` (drawdown, open positions, and
    volume) so the top-level status cannot contradict the factual limits block.
    """
    if acc.get("status") == "ERROR":
        status = "ALERT"
    elif acc.get("status") == "PAUSED":
        status = "WARNING"
    else:
        limits = limits_status(acc, open_positions=open_positions)
        any_breach = (
            bool(limits.get("drawdown", {}).get("breached"))
            or bool(limits.get("open_positions", {}).get("breached"))
            or bool(limits.get("position_volume", {}).get("breached"))
        )
        status = "WARNING" if any_breach else "OK"
    if bridge_ok is False and status == "OK":
        status = "WARNING"
    if acc.get("stale") and status == "OK":
        status = "WARNING"
    return status


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def summarize_open_positions(positions: list[dict] | None) -> list[dict]:
    """Compact open-position rows via ``positions_passthrough`` (no remapping)."""
    rows = []
    for p in positions_passthrough(positions or []):
        floating = float(p.get("profit", 0) or 0) + float(p.get("swap", 0) or 0)
        rows.append({
            "symbol": p.get("symbol"),
            "side": p.get("side"),
            "volume": p.get("volume"),
            "floating_pnl": round(floating, 2),
            "magic": p.get("magic"),
            "ticket": p.get("ticket"),
        })
    return rows


def closed_trades_since(
    trades: list[dict],
    *,
    since_iso: str | None,
) -> list[dict]:
    """Trades closed after ``since_iso`` (same account). If no prior report, empty."""
    if not since_iso:
        return []
    since = _parse_iso(since_iso)
    if since is None:
        return []
    out = []
    for t in trades or []:
        closed = _parse_iso(t.get("close_time"))
        if closed is None:
            continue
        if closed > since:
            out.append({
                "symbol": t.get("symbol"),
                "side": t.get("side"),
                "pnl": t.get("pnl"),
                "lots": t.get("lots"),
                "close_time": t.get("close_time"),
                "magic": t.get("magic"),
                "strategy": t.get("strategy"),
            })
    return out


def limits_status(acc: dict, *, open_positions: list[dict] | None = None) -> dict:
    """Factual state vs each configured risk limit (no recommendations)."""
    limits = acc.get("risk_limits") or {}
    max_dd = float(limits.get("max_daily_loss_pct", 5.0))
    max_pos = int(limits.get("max_open_positions", 20))
    max_lots = float(limits.get("max_position_size_lots", 1.0))

    current_dd = abs(float(acc.get("current_drawdown", 0.0) or 0.0))
    pos_count = int(acc.get("open_positions", 0) or 0)
    if open_positions is not None:
        pos_count = len(open_positions)
        largest = max(
            (float(p.get("volume", 0) or 0) for p in open_positions),
            default=0.0,
        )
    else:
        largest = None  # not available without position list

    dd_breach = current_dd >= max_dd
    pos_breach = pos_count >= max_pos
    vol_breach = (largest is not None) and (largest >= max_lots)

    return {
        "drawdown": {
            "limit_pct": max_dd,
            "current_pct": round(current_dd, 2),
            "breached": dd_breach,
        },
        "open_positions": {
            "limit": max_pos,
            "current": pos_count,
            "breached": pos_breach,
        },
        "position_volume": {
            "limit_lots": max_lots,
            "largest_open_lots": largest if largest is not None else "not_available",
            "breached": vol_breach if largest is not None else False,
        },
    }


def compare_with_previous(
    acc: dict,
    previous: dict | None,
    *,
    bridge_ok: bool | None,
) -> dict | None:
    """Factual deltas vs the previous report for the **same** account only."""
    if previous is None:
        return None
    if previous.get("account_id") and previous.get("account_id") != acc.get("id"):
        # Guard: never compare across accounts.
        return None

    prev_metrics = previous.get("metrics") or {}

    def _delta(curr, prev):
        if curr is None or prev is None:
            return None
        try:
            return round(float(curr) - float(prev), 2)
        except (TypeError, ValueError):
            return None

    prev_bridge = previous.get("bridge_ok")
    if bridge_ok is True and prev_bridge is False:
        link = "restored"
    elif bridge_ok is False and prev_bridge is not False:
        link = "lost"
    elif bridge_ok is False and prev_bridge is False:
        link = "still_down"
    else:
        link = "unchanged"

    return {
        "previous_report_id": previous.get("id"),
        "previous_created_at": previous.get("created_at"),
        "equity": {
            "previous": prev_metrics.get("equity"),
            "current": acc.get("equity"),
            "delta": _delta(acc.get("equity"), prev_metrics.get("equity")),
        },
        "daily_pnl": {
            "previous": prev_metrics.get("daily_pnl"),
            "current": acc.get("daily_pnl"),
            "delta": _delta(acc.get("daily_pnl"), prev_metrics.get("daily_pnl")),
        },
        "open_positions": {
            "previous": prev_metrics.get("open_positions"),
            "current": acc.get("open_positions"),
            "delta": _delta(acc.get("open_positions"), prev_metrics.get("open_positions")),
        },
        "current_drawdown": {
            "previous": prev_metrics.get("current_drawdown"),
            "current": acc.get("current_drawdown"),
            "delta": _delta(acc.get("current_drawdown"), prev_metrics.get("current_drawdown")),
        },
        "bridge_link": link,
    }


def factual_conclusion(
    acc: dict,
    *,
    status: str,
    limits: dict,
    comparison: dict | None,
    closed_count: int,
    bridge_ok: bool | None,
) -> str:
    """One-line factual summary — no advice, no predictions."""
    login = acc.get("login")
    parts = [f"Account {login}: status {status}"]
    if bridge_ok is False:
        parts.append("bridge unavailable")
    elif acc.get("stale"):
        parts.append("data from cache")
    breaches = []
    if limits.get("drawdown", {}).get("breached"):
        breaches.append("drawdown limit")
    if limits.get("open_positions", {}).get("breached"):
        breaches.append("open-positions limit")
    if limits.get("position_volume", {}).get("breached"):
        breaches.append("volume limit")
    if breaches:
        parts.append("breached " + ", ".join(breaches))
    else:
        parts.append("within configured limits")
    if comparison and comparison.get("equity", {}).get("delta") is not None:
        parts.append(f"equity Δ {comparison['equity']['delta']}")
    parts.append(f"{closed_count} closed trade(s) since prior report")
    return "; ".join(parts) + "."


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
    positions: list[dict] | None = None,
    deals: list[dict] | None = None,
    previous_report: dict | None = None,
    label_overrides: dict[int, str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build one report document for a single account (no secrets)."""
    if acc.get("stale"):
        data_origin = "cache"
    elif bridge_ok:
        data_origin = "live"
    elif bridge_ok is False:
        data_origin = "cache"
    else:
        data_origin = "live"  # mock mode

    snapshot_at = generated_at or datetime.now(timezone.utc).isoformat()

    open_rows = summarize_open_positions(positions)
    positions_for_limits = open_rows if positions is not None else None
    status = (
        status_override
        or account_report_status(
            acc, bridge_ok=bridge_ok, open_positions=positions_for_limits
        )
    ).upper()
    # Prefer live mapped trades from deals; fall back to pre-mapped trades on mock.
    if deals is not None:
        all_trades = trades_from_deals(deals, label_overrides=label_overrides)
    else:
        all_trades = list(acc.get("_trades") or [])

    since = (previous_report or {}).get("created_at") if previous_report else None
    # Only use previous when it belongs to this account.
    if previous_report and previous_report.get("account_id") not in (None, acc.get("id")):
        previous_report = None
        since = None

    closed_rows = closed_trades_since(all_trades, since_iso=since)
    limits = limits_status(acc, open_positions=positions_for_limits)
    comparison = compare_with_previous(acc, previous_report, bridge_ok=bridge_ok)

    ea_rows: list[dict] = []
    if positions is not None or deals is not None:
        ea_rows = eas_from_bridge(
            account_id=str(acc["id"]),
            login=int(acc.get("login") or 0),
            positions=positions or [],
            deals=deals or [],
            label_overrides=label_overrides,
        )

    if message_override:
        message = message_override
    else:
        message = factual_conclusion(
            acc,
            status=status,
            limits=limits,
            comparison=comparison,
            closed_count=len(closed_rows),
            bridge_ok=bridge_ok,
        )

    return {
        "supervisor": supervisor,
        "ecosystem": ecosystem,
        "account_id": acc["id"],
        "login": acc.get("login"),
        "server": acc.get("broker") or acc.get("server"),
        "currency": acc.get("currency"),
        "snapshot_at": snapshot_at,
        "status": status,
        "backend_ok": True if backend_ok is None else backend_ok,
        "bridge_ok": bridge_ok if bridge_ok is not None else None,
        "dashboard_ok": True if dashboard_ok is None else dashboard_ok,
        "message": message,
        "conclusion": message if not message_override else factual_conclusion(
            acc,
            status=status,
            limits=limits,
            comparison=comparison,
            closed_count=len(closed_rows),
            bridge_ok=bridge_ok,
        ),
        "source": source,
        "data_origin": data_origin,
        "account_status": acc.get("status"),
        # Explicitly not available from current sources — do not invent.
        "account_type": "not_available",
        "session": "not_available",
        "metrics": {
            "equity": acc.get("equity"),
            "balance": acc.get("balance"),
            "daily_pnl": acc.get("daily_pnl"),
            "open_positions": (
                len(open_rows) if positions is not None else acc.get("open_positions")
            ),
            "current_drawdown": acc.get("current_drawdown"),
            "max_drawdown": acc.get("max_drawdown"),
            "risk_limits": acc.get("risk_limits") or {},
        },
        "open_positions": open_rows,
        "closed_trades_since_previous": closed_rows,
        "limits_status": limits,
        "comparison_to_previous": comparison,
        "eas": [
            {
                "magic": e.get("magic"),
                "label": e.get("label"),
                "open_positions": e.get("open_positions"),
                "floating_pnl": e.get("floating_pnl"),
                "realized_pnl": e.get("realized_pnl"),
            }
            for e in ea_rows
        ],
    }

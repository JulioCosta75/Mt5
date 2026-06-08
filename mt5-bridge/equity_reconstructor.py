"""Reconstruct an equity curve from MT5 closed-deal history.

Algorithm:
  1. Fetch closed deals over the lookback window (default 90 days).
  2. Walk forward, keeping a running cumulative P&L (+swap+commission).
  3. Define the historical balance series as: balance(t) = current_balance - (cumulative_pnl_total - cumulative_pnl_at_t)
  4. The equity series is approximated by the balance series at each deal close
     (intra-trade equity isn't preserved by MT5 server-side).

This produces a useful curve immediately. Going forward, live snapshots from
snapshot_recorder.py refine it by adding intra-bar equity points.
"""
from __future__ import annotations

from datetime import datetime, timezone


def reconstruct(deals: list[dict], current_balance: float) -> list[dict]:
    """Return [{'t': iso, 'equity': float}, ...] in chronological order."""
    if not deals:
        # Anchor a single point at "now" so charts don't crash.
        return [{"t": datetime.now(timezone.utc).isoformat(), "equity": current_balance}]

    # sort by time ascending
    sorted_deals = sorted(deals, key=lambda d: d["time"])
    # cumulative P&L over all deals (final state should match current_balance)
    pnl_total = sum((d["profit"] + d["swap"] + d["commission"]) for d in sorted_deals)
    # back-derive the starting balance
    start_balance = current_balance - pnl_total

    series: list[dict] = []
    running = start_balance
    # initial anchor
    first_t = sorted_deals[0]["time"]
    series.append({"t": first_t, "equity": round(running, 2)})

    for d in sorted_deals:
        running += d["profit"] + d["swap"] + d["commission"]
        series.append({"t": d["time"], "equity": round(running, 2)})

    return series


def merge_with_snapshots(reconstructed: list[dict], snapshots: list[dict]) -> list[dict]:
    """Merge reconstructed (sparse, deal-driven) with live snapshots (dense).

    Snapshots win for any timestamp >= first snapshot time.
    """
    if not snapshots:
        return reconstructed
    first_snap_t = snapshots[0]["t"]
    head = [p for p in reconstructed if p["t"] < first_snap_t]
    return head + snapshots

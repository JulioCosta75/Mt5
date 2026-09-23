"""Fixed-rule alert evaluation for Phase 2 (per account).

Rules (no ML / no predictions):
  * drawdown >= configured limit
  * open positions >= configured limit
  * open position volume >= configured lot limit
  * account status ERROR
  * bridge inaccessible

States: ``active`` → ``acknowledged`` (human) → ``resolved`` (condition cleared).
Never recreate the same (account_id, rule_key) while it is still active or
acknowledged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


RULE_DRAWDOWN = "drawdown_limit"
RULE_OPEN_POSITIONS = "open_positions_limit"
RULE_VOLUME = "position_volume_limit"
RULE_ACCOUNT_ERROR = "account_error"
RULE_BRIDGE_DOWN = "bridge_unreachable"

OPEN_STATES = frozenset({"active", "acknowledged"})


def _limits(acc: dict) -> dict:
    return acc.get("risk_limits") or {}


def evaluate_account_conditions(
    acc: dict,
    *,
    bridge_ok: bool | None,
    open_positions: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """Return currently-firing alert candidates for one account.

    Each item: ``{rule_key, severity, message, account_id}``.
    """
    account_id = acc.get("id")
    login = acc.get("login")
    limits = _limits(acc)
    firing: list[dict[str, Any]] = []

    # Bridge down — never silent; CRITICAL. Also covers "stale/outdated" path
    # when the live bridge is unreachable (status must not present as OK).
    if bridge_ok is False:
        firing.append({
            "rule_key": RULE_BRIDGE_DOWN,
            "severity": "CRITICAL",
            "account_id": account_id,
            "message": (
                f"Account {login}: MT5 bridge inaccessible — "
                "data may be outdated; status cannot be OK."
            ),
        })

    if acc.get("status") == "ERROR":
        firing.append({
            "rule_key": RULE_ACCOUNT_ERROR,
            "severity": "CRITICAL",
            "account_id": account_id,
            "message": f"Account {login}: account status is ERROR.",
        })

    max_dd = float(limits.get("max_daily_loss_pct", 5.0))
    current_dd = abs(float(acc.get("current_drawdown", 0.0) or 0.0))
    if current_dd >= max_dd:
        firing.append({
            "rule_key": RULE_DRAWDOWN,
            "severity": "WARNING",
            "account_id": account_id,
            "message": (
                f"Account {login}: drawdown {current_dd}% "
                f">= limit {max_dd}%."
            ),
        })

    max_pos = int(limits.get("max_open_positions", 20))
    pos_count = int(acc.get("open_positions", 0) or 0)
    if open_positions is not None:
        pos_count = len(open_positions)
    if pos_count >= max_pos:
        firing.append({
            "rule_key": RULE_OPEN_POSITIONS,
            "severity": "WARNING",
            "account_id": account_id,
            "message": (
                f"Account {login}: open positions {pos_count} "
                f">= limit {max_pos}."
            ),
        })

    max_lots = float(limits.get("max_position_size_lots", 1.0))
    if open_positions is not None:
        largest = max(
            (float(p.get("volume", 0) or 0) for p in open_positions),
            default=0.0,
        )
        if largest >= max_lots:
            firing.append({
                "rule_key": RULE_VOLUME,
                "severity": "WARNING",
                "account_id": account_id,
                "message": (
                    f"Account {login}: largest open volume {largest} lots "
                    f">= limit {max_lots} lots."
                ),
            })

    return firing


def reconcile_alerts(
    *,
    existing_open: list[dict],
    firing: list[dict],
    account_id: str,
) -> dict[str, list[dict]]:
    """Reconcile open alerts with currently firing conditions for one account.

    Returns ``{create: [...], resolve: [...], keep: [...]}``.
    Does **not** recreate a rule that is already active or acknowledged.
    """
    open_by_rule = {
        a["rule_key"]: a
        for a in existing_open
        if a.get("account_id") == account_id and a.get("state") in OPEN_STATES
    }
    firing_by_rule = {c["rule_key"]: c for c in firing}

    create: list[dict] = []
    resolve: list[dict] = []
    keep: list[dict] = []

    for rule_key, candidate in firing_by_rule.items():
        current = open_by_rule.get(rule_key)
        if current is None:
            create.append(candidate)
        else:
            keep.append(current)

    for rule_key, alert in open_by_rule.items():
        if rule_key not in firing_by_rule:
            resolve.append(alert)

    return {"create": create, "resolve": resolve, "keep": keep}


def to_api_alert(doc: dict) -> dict[str, Any]:
    """Map a stored alert to the frontend/API contract."""
    state = doc.get("state") or "active"
    return {
        "id": doc["id"],
        "severity": doc["severity"],
        "account_id": doc["account_id"],
        "message": doc["message"],
        "timestamp": doc.get("created_at") or doc.get("timestamp"),
        "acknowledged": state in ("acknowledged", "resolved"),
        "state": state,
        "rule_key": doc.get("rule_key"),
        "acknowledged_at": doc.get("acknowledged_at"),
        "resolved_at": doc.get("resolved_at"),
    }


def to_api_alerts(docs: list[dict]) -> list[dict[str, Any]]:
    return [to_api_alert(d) for d in docs]


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


def alerts_events_since(
    alerts: list[dict],
    *,
    since_iso: str | None,
    account_id: str | None = None,
) -> list[dict[str, Any]]:
    """Factual alert events after ``since_iso`` — same window as closed trades.

    Emits one row per timestamp (created / acknowledged / resolved) that falls
    strictly after the previous report. ``state`` is the state *at that event*
    (active on create, acknowledged, resolved). Empty when there is no prior
    report (``since_iso`` is None) — never invents data.
    """
    if not since_iso:
        return []
    since = _parse_iso(since_iso)
    if since is None:
        return []

    events: list[dict[str, Any]] = []
    for alert in alerts or []:
        if account_id and alert.get("account_id") not in (None, account_id):
            continue
        base = {
            "rule_key": alert.get("rule_key"),
            "severity": alert.get("severity"),
            "message": alert.get("message"),
        }
        for field, state_at_event in (
            ("created_at", "active"),
            ("acknowledged_at", "acknowledged"),
            ("resolved_at", "resolved"),
        ):
            ts = _parse_iso(alert.get(field))
            if ts is None or ts <= since:
                continue
            events.append({
                **base,
                "state": state_at_event,
                "event_at": alert.get(field),
            })

    events.sort(key=lambda e: str(e.get("event_at") or ""))
    return events


async def load_alerts_since_previous(
    store: Any,
    *,
    account_id: str,
    since_iso: str | None,
) -> list[dict[str, Any]]:
    """Load account alerts via the existing store ``list`` API, then window them."""
    if not since_iso or not account_id:
        return []
    rows = await store.list(account_id=account_id, limit=500)
    return alerts_events_since(rows, since_iso=since_iso, account_id=account_id)


async def evaluate_and_persist_account_alerts(
    store: Any,
    acc: dict,
    *,
    bridge_ok: bool | None,
    open_positions: list[dict] | None = None,
) -> dict[str, list[dict]]:
    """Evaluate fixed rules for one account and reconcile against the store.

    Never recreates an (account_id, rule_key) that is still active or
    acknowledged. Resolves open alerts whose condition has cleared.
    """
    account_id = acc.get("id")
    if not account_id:
        raise ValueError("account_id is required for alert evaluation")

    existing = await store.list_open(account_id=account_id)
    firing = evaluate_account_conditions(
        acc, bridge_ok=bridge_ok, open_positions=open_positions
    )
    plan = reconcile_alerts(
        existing_open=existing, firing=firing, account_id=account_id
    )

    created: list[dict] = []
    for candidate in plan["create"]:
        created.append(await store.create(candidate))

    resolved: list[dict] = []
    for alert in plan["resolve"]:
        row = await store.resolve(alert["id"])
        if row is not None:
            resolved.append(row)

    return {"created": created, "resolved": resolved, "kept": plan["keep"]}

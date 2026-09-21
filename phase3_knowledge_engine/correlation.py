"""Gate 5 extension — isolated negative-day coincidence between two EAs.

For a pair of EAs, take the last 90 days of Block 1 evidence, the calendar
days on which each EA had net-negative PnL, and the share of those days that
coincide (intersection / union). At or above ``EA_CORRELATION_FLAG_THRESHOLD``
the pair is marked ``paired`` — an observed fact, not a recommendation.

Missing profile or no usable history → ``insufficient_data``. Coincidence is
then omitted entirely — never invented as 0%.

Does not mount HTTP, touch Phase 2, or enable
``PHASE3_KNOWLEDGE_ENGINE_ENABLED``.

Examples::

    python -m phase3_knowledge_engine.correlation \\
        --account demo-51234567 --ea-a london-scalper --ea-b ny-scalper
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from phase3_knowledge_engine.config import (
    DEFAULT_KNOWLEDGE_DB_PATH,
    EA_CORRELATION_FLAG_THRESHOLD,
)
from phase3_knowledge_engine.domain.entities import EvidenceItem
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.insights import resolve_account

STATUS_PAIRED = "paired"
STATUS_NOT_PAIRED = "not_paired"
STATUS_INSUFFICIENT = "insufficient_data"
INSUFFICIENT_LABEL = "dados insuficientes"
LOOKBACK_DAYS = 90


@dataclass(frozen=True)
class CorrelationResult:
    """Observed coincidence of negative-PnL days. Never a recommendation."""

    account: str
    ea_a_key: str | None
    ea_b_key: str | None
    status: str
    coincidence: float | None
    is_paired: bool
    negative_days_a: int | None
    negative_days_b: int | None
    coinciding_days: int | None
    union_days: int | None
    threshold: float
    reason: str


def _utc_date(value: datetime) -> date:
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def daily_net_pnl(items: list[EvidenceItem]) -> dict[date, float]:
    """Sum stored PnL by UTC calendar day. Skips items with no pnl."""
    by_day: dict[date, float] = {}
    for item in items:
        if item.pnl is None:
            continue
        day = _utc_date(item.occurred_at)
        by_day[day] = by_day.get(day, 0.0) + float(item.pnl)
    return by_day


def negative_pnl_days(items: list[EvidenceItem]) -> set[date]:
    """Calendar days whose net PnL is strictly negative."""
    return {day for day, pnl in daily_net_pnl(items).items() if pnl < 0}


def coincidence_ratio(days_a: set[date], days_b: set[date]) -> float | None:
    """Intersection / union of two day sets. None when the union is empty."""
    union = days_a | days_b
    if not union:
        return None
    return len(days_a & days_b) / len(union)


def _insufficient(
    *,
    account: str,
    ea_a_key: str | None,
    ea_b_key: str | None,
    reason: str,
    threshold: float,
) -> CorrelationResult:
    return CorrelationResult(
        account=account,
        ea_a_key=ea_a_key,
        ea_b_key=ea_b_key,
        status=STATUS_INSUFFICIENT,
        coincidence=None,
        is_paired=False,
        negative_days_a=None,
        negative_days_b=None,
        coinciding_days=None,
        union_days=None,
        threshold=threshold,
        reason=reason,
    )


def _window(now: datetime) -> tuple[datetime, datetime]:
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    return moment - timedelta(days=LOOKBACK_DAYS), moment


def correlate_ea_pair(
    *,
    repository: KnowledgeRepositoryPort,
    account: str,
    ea_a: str,
    ea_b: str,
    now: datetime | None = None,
    threshold: float | None = None,
) -> CorrelationResult:
    """Compare negative-PnL days for two EAs in the last ``LOOKBACK_DAYS``.

    ``coincidence`` is omitted when either EA lacks usable history or the
    union of negative days is empty — never reported as 0% in those cases.
    """
    limit = EA_CORRELATION_FLAG_THRESHOLD if threshold is None else float(threshold)
    label = (account or "").strip()
    moment = now if now is not None else datetime.now(timezone.utc)
    started, ended = _window(moment)

    profile_a = resolve_account(repository, ea_a)
    profile_b = resolve_account(repository, ea_b)
    key_a = profile_a.ea_key if profile_a is not None else (ea_a or "").strip() or None
    key_b = profile_b.ea_key if profile_b is not None else (ea_b or "").strip() or None

    if profile_a is None:
        return _insufficient(
            account=label,
            ea_a_key=key_a,
            ea_b_key=key_b,
            reason=f"{INSUFFICIENT_LABEL}: no EA profile matching ea_a={ea_a!r}.",
            threshold=limit,
        )
    if profile_b is None:
        return _insufficient(
            account=label,
            ea_a_key=key_a,
            ea_b_key=key_b,
            reason=f"{INSUFFICIENT_LABEL}: no EA profile matching ea_b={ea_b!r}.",
            threshold=limit,
        )

    items_a = repository.list_evidence_for_ea(
        profile_a.id, occurred_after=started, occurred_before=ended
    )
    items_b = repository.list_evidence_for_ea(
        profile_b.id, occurred_after=started, occurred_before=ended
    )
    nets_a = daily_net_pnl(items_a)
    nets_b = daily_net_pnl(items_b)
    if not nets_a:
        return _insufficient(
            account=label,
            ea_a_key=profile_a.ea_key,
            ea_b_key=profile_b.ea_key,
            reason=(
                f"{INSUFFICIENT_LABEL}: ea_key={profile_a.ea_key!r} has no "
                f"daily net PnL in the last {LOOKBACK_DAYS} days."
            ),
            threshold=limit,
        )
    if not nets_b:
        return _insufficient(
            account=label,
            ea_a_key=profile_a.ea_key,
            ea_b_key=profile_b.ea_key,
            reason=(
                f"{INSUFFICIENT_LABEL}: ea_key={profile_b.ea_key!r} has no "
                f"daily net PnL in the last {LOOKBACK_DAYS} days."
            ),
            threshold=limit,
        )

    days_a = {day for day, pnl in nets_a.items() if pnl < 0}
    days_b = {day for day, pnl in nets_b.items() if pnl < 0}
    ratio = coincidence_ratio(days_a, days_b)
    if ratio is None:
        return _insufficient(
            account=label,
            ea_a_key=profile_a.ea_key,
            ea_b_key=profile_b.ea_key,
            reason=(
                f"{INSUFFICIENT_LABEL}: neither EA has a net-negative day "
                f"in the last {LOOKBACK_DAYS} days."
            ),
            threshold=limit,
        )

    coinciding = len(days_a & days_b)
    union = len(days_a | days_b)
    paired = ratio >= limit
    status = STATUS_PAIRED if paired else STATUS_NOT_PAIRED
    reason = (
        f"coincidence={ratio:.3f} of negative-PnL days "
        f"(coinciding={coinciding}, union={union}, threshold={limit})."
    )
    return CorrelationResult(
        account=label,
        ea_a_key=profile_a.ea_key,
        ea_b_key=profile_b.ea_key,
        status=status,
        coincidence=ratio,
        is_paired=paired,
        negative_days_a=len(days_a),
        negative_days_b=len(days_b),
        coinciding_days=coinciding,
        union_days=union,
        threshold=limit,
        reason=reason,
    )


def format_correlation_line(result: CorrelationResult) -> str:
    if result.status == STATUS_INSUFFICIENT:
        coinc = "omitted"
    elif result.coincidence is None:
        coinc = "omitted"
    else:
        coinc = f"{result.coincidence:.3f}"
    return (
        f"account={result.account}  ea_a={result.ea_a_key}  ea_b={result.ea_b_key}\n"
        f"  status={result.status}  is_paired={result.is_paired}  "
        f"coincidence={coinc}  threshold={result.threshold}\n"
        f"  {result.reason}"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.correlation",
        description=(
            "Gate 5 — coincidence of net-negative days between two EAs "
            "(read-only; no state changes, flag untouched)."
        ),
    )
    p.add_argument(
        "--account",
        required=True,
        metavar="ID",
        help="Operator account label for this pair (same knowledge.db)",
    )
    p.add_argument(
        "--ea-a",
        required=True,
        dest="ea_a",
        metavar="ID",
        help="First EA profile UUID or ea_key",
    )
    p.add_argument(
        "--ea-b",
        required=True,
        dest="ea_b",
        metavar="ID",
        help="Second EA profile UUID or ea_key",
    )
    p.add_argument(
        "--db",
        default=DEFAULT_KNOWLEDGE_DB_PATH,
        help=f"knowledge.db path (default: {DEFAULT_KNOWLEDGE_DB_PATH})",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = KnowledgeRepository(args.db)
    result = correlate_ea_pair(
        repository=repo,
        account=args.account,
        ea_a=args.ea_a,
        ea_b=args.ea_b,
    )
    print(format_correlation_line(result))
    return 0


# Re-export for tests that pin the lookback window.
__all__ = [
    "CorrelationResult",
    "LOOKBACK_DAYS",
    "STATUS_INSUFFICIENT",
    "STATUS_NOT_PAIRED",
    "STATUS_PAIRED",
    "INSUFFICIENT_LABEL",
    "coincidence_ratio",
    "correlate_ea_pair",
    "daily_net_pnl",
    "format_correlation_line",
    "main",
    "negative_pnl_days",
]


if __name__ == "__main__":
    raise SystemExit(main())

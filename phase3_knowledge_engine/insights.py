"""Gate 5 Stage 1 — isolated insights from validated Knowledge (Levels A+B).

Level A: format factual statements from ``ValidationState.KNOWLEDGE`` records
only (statement, sample_size, confidence_score, last_reviewed_at).

Level B: compare each record's ``context_signature`` (EA, version, session,
symbol) with a caller-supplied current context. Match →
``is_context_active_now=True``. No match or missing signature → False.

Never invents records. Never interprets beyond what is stored. Does not
mount HTTP, touch Phase 2, or enable ``PHASE3_KNOWLEDGE_ENGINE_ENABLED``.

Examples::

    python -m phase3_knowledge_engine.insights --account london-scalper
    python -m phase3_knowledge_engine.insights --account london-scalper \\
        --session London --symbol XAUUSD
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from phase3_knowledge_engine.application.services import KnowledgeEngineService
from phase3_knowledge_engine.config import DEFAULT_KNOWLEDGE_DB_PATH
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


@dataclass(frozen=True)
class CurrentContext:
    """Caller-supplied live context for Level B. All fields optional."""

    session: str | None = None
    symbol: str | None = None
    ea_version: str | None = None
    ea_active: bool | None = None


@dataclass(frozen=True)
class ParsedContextSignature:
    ea_profile_id: str
    ea_version: str
    session: str
    symbol: str


@dataclass(frozen=True)
class Insight:
    """One validated Knowledge record, formatted (A) and context-flagged (B)."""

    knowledge_record_id: UUID
    statement: str
    sample_size: int
    confidence_score: float
    last_reviewed_at: datetime | None
    context_signature: str | None
    is_context_active_now: bool
    formatted: str


def format_level_a(record: KnowledgeRecord) -> str:
    """Factual sentence from a KNOWLEDGE record. No extra interpretation."""
    reviewed = (
        record.last_reviewed_at.isoformat()
        if record.last_reviewed_at is not None
        else "unknown"
    )
    return (
        f"{record.statement} "
        f"(sample_size={record.sample_size}, "
        f"confidence_score={record.confidence_score}, "
        f"last_reviewed_at={reviewed})."
    )


def parse_context_signature(signature: str | None) -> ParsedContextSignature | None:
    """Inverse of ``KnowledgeEngineService.compute_context_signature``.

    Layout: ``{ea_profile_id}-{ea_version}-{session}-{symbol}``.
    ``ea_profile_id`` is a 36-character UUID. Version/session may be empty.
    """
    if not signature:
        return None
    sig = signature.strip()
    if len(sig) < 36:
        return None
    ea_id = sig[:36]
    try:
        UUID(ea_id)
    except ValueError:
        return None
    rest = sig[36:]
    if rest.startswith("-"):
        rest = rest[1:]
    parts = rest.split("-")
    if len(parts) < 2:
        return None
    symbol = parts[-1]
    session = parts[-2]
    version = "-".join(parts[:-2])
    return ParsedContextSignature(
        ea_profile_id=ea_id,
        ea_version=version,
        session=session,
        symbol=symbol,
    )


def _norm(value: str | None) -> str:
    return (value or "").strip()


def is_context_active_now(
    signature: str | None,
    current: CurrentContext | None,
    *,
    ea_profile_id: UUID | None = None,
) -> bool:
    """True only when supplied current-context fields match the signature.

    Requires at least session and symbol on ``current`` (Gate 5 Level B).
    If ``ea_active`` is False, never active. Missing/unparseable signature
    is not a match — never guessed.
    """
    if current is None:
        return False
    if current.ea_active is False:
        return False
    if current.session is None or current.symbol is None:
        return False
    parsed = parse_context_signature(signature)
    if parsed is None:
        return False
    if _norm(parsed.session) != _norm(current.session):
        return False
    if _norm(parsed.symbol) != _norm(current.symbol):
        return False
    if current.ea_version is not None and _norm(parsed.ea_version) != _norm(current.ea_version):
        return False
    if ea_profile_id is not None and parsed.ea_profile_id != str(ea_profile_id):
        return False
    return True


def resolve_account(
    repository: KnowledgeRepositoryPort,
    account: str,
) -> EAKnowledgeProfile | None:
    """Resolve ``--account`` as ea_profile UUID or ea_key. No invention."""
    raw = (account or "").strip()
    if not raw:
        return None
    try:
        profile = repository.get_ea_profile(UUID(raw))
        if profile is not None:
            return profile
    except ValueError:
        pass
    return repository.get_ea_profile_by_ea_key(raw)


def list_insights(
    *,
    repository: KnowledgeRepositoryPort,
    ea_profile_id: UUID | None = None,
    current_context: CurrentContext | None = None,
    limit: int = 100,
) -> list[Insight]:
    """Level A+B insights from KNOWLEDGE records only.

    Empty list when nothing is validated — never synthesises rows.
    """
    records = repository.list_knowledge_records_by_state(
        ValidationState.KNOWLEDGE,
        ea_profile_id=ea_profile_id,
        limit=limit,
    )
    insights: list[Insight] = []
    for record in records:
        if record.validation_state != ValidationState.KNOWLEDGE.value:
            continue
        active = is_context_active_now(
            record.context_signature,
            current_context,
            ea_profile_id=record.ea_profile_id,
        )
        insights.append(
            Insight(
                knowledge_record_id=record.id,
                statement=record.statement,
                sample_size=record.sample_size,
                confidence_score=record.confidence_score,
                last_reviewed_at=record.last_reviewed_at,
                context_signature=record.context_signature,
                is_context_active_now=active,
                formatted=format_level_a(record),
            )
        )
    return insights


def format_insight_line(insight: Insight) -> str:
    flag = "active_now" if insight.is_context_active_now else "not_active_now"
    return (
        f"id={insight.knowledge_record_id}  "
        f"is_context_active_now={insight.is_context_active_now} ({flag})\n"
        f"  {insight.formatted}"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.insights",
        description=(
            "Gate 5 Stage 1 — list validated Knowledge insights for an account/EA "
            "(read-only; no state changes, flag untouched)."
        ),
    )
    p.add_argument(
        "--account",
        required=True,
        metavar="ID",
        help="EA profile UUID or ea_key in knowledge.db",
    )
    p.add_argument(
        "--session",
        default=None,
        help="Current session for Level B (e.g. London)",
    )
    p.add_argument(
        "--symbol",
        default=None,
        help="Current symbol for Level B (e.g. XAUUSD)",
    )
    p.add_argument(
        "--ea-version",
        default=None,
        dest="ea_version",
        help="Optional current EA version for Level B",
    )
    p.add_argument(
        "--ea-active",
        default=None,
        choices=("true", "false"),
        help="Optional EA activity flag for Level B (true/false)",
    )
    p.add_argument(
        "--db",
        default=DEFAULT_KNOWLEDGE_DB_PATH,
        help=f"knowledge.db path (default: {DEFAULT_KNOWLEDGE_DB_PATH})",
    )
    p.add_argument("--limit", type=int, default=100, help="Max rows (default 100)")
    return p


def _ea_active_from_arg(raw: str | None) -> bool | None:
    if raw is None:
        return None
    return raw == "true"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = KnowledgeRepository(args.db)
    profile = resolve_account(repo, args.account)
    if profile is None:
        print(f"No EA profile matching account={args.account!r}.", file=sys.stderr)
        return 0
    current = CurrentContext(
        session=args.session,
        symbol=args.symbol,
        ea_version=args.ea_version,
        ea_active=_ea_active_from_arg(args.ea_active),
    )
    rows = list_insights(
        repository=repo,
        ea_profile_id=profile.id,
        current_context=current,
        limit=args.limit,
    )
    if not rows:
        print("No validated knowledge records.")
        return 0
    print(f"{len(rows)} validated insight(s) for ea_key={profile.ea_key}:\n")
    for i, insight in enumerate(rows, start=1):
        print(f"[{i}] {format_insight_line(insight)}")
        print()
    return 0


# Re-export for tests that compare against the canonical grouping key.
compute_context_signature = KnowledgeEngineService.compute_context_signature


if __name__ == "__main__":
    raise SystemExit(main())

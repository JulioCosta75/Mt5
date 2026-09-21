"""Gate 5 extension — isolated graveyard of invalidated conclusions.

Lists ``ValidationState.INVALIDATED_CONCLUSION`` records only. Each entry
shows the original statement, when it was invalidated, who decided, and the
justification from the existing audit trail for that transition.

Never invents records or justifications. Does not mount HTTP, touch Phase 2,
or enable ``PHASE3_KNOWLEDGE_ENGINE_ENABLED``.

Examples::

    python -m phase3_knowledge_engine.graveyard --account london-scalper
    python -m phase3_knowledge_engine.graveyard --account <ea-profile-uuid>
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from phase3_knowledge_engine.config import DEFAULT_KNOWLEDGE_DB_PATH
from phase3_knowledge_engine.domain.entities import AuditTrailEntry, KnowledgeRecord
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
from phase3_knowledge_engine.insights import resolve_account


@dataclass(frozen=True)
class GraveyardEntry:
    """One invalidated conclusion, with audit metadata when present."""

    knowledge_record_id: UUID
    statement: str
    invalidated_at: datetime | None
    decided_by: str | None
    justification: str | None
    formatted: str


def invalidation_audit(
    repository: KnowledgeRepositoryPort,
    knowledge_record_id: UUID,
) -> AuditTrailEntry | None:
    """Latest audit entry that moved the record to INVALIDATED_CONCLUSION.

    Reuses ``list_audit_trail``. Returns None when that transition was never
    recorded — never synthesises actor, time, or justification.
    """
    target = ValidationState.INVALIDATED_CONCLUSION.value
    matches = [
        entry
        for entry in repository.list_audit_trail(knowledge_record_id)
        if entry.to_state == target
    ]
    return matches[-1] if matches else None


def format_graveyard_entry(
    record: KnowledgeRecord,
    audit: AuditTrailEntry | None,
) -> str:
    """Factual sentence from an invalidated record. No extra interpretation."""
    invalidated_at = (
        audit.transitioned_at.isoformat() if audit is not None else "unknown"
    )
    decided_by = audit.actor if audit is not None else "unknown"
    justification = (
        audit.justification if audit is not None and audit.justification else ""
    )
    return (
        f"{record.statement} "
        f"(invalidated_at={invalidated_at}, "
        f"decided_by={decided_by}, "
        f"justification={justification!r})."
    )


def list_graveyard(
    *,
    repository: KnowledgeRepositoryPort,
    ea_profile_id: UUID | None = None,
    limit: int = 100,
) -> list[GraveyardEntry]:
    """Invalidated conclusions for one EA (or all, if ea_profile_id is None).

    Empty list when nothing is invalidated — never synthesises rows.
    """
    records = repository.list_knowledge_records_by_state(
        ValidationState.INVALIDATED_CONCLUSION,
        ea_profile_id=ea_profile_id,
        limit=limit,
    )
    entries: list[GraveyardEntry] = []
    target = ValidationState.INVALIDATED_CONCLUSION.value
    for record in records:
        if record.validation_state != target:
            continue
        audit = invalidation_audit(repository, record.id)
        entries.append(
            GraveyardEntry(
                knowledge_record_id=record.id,
                statement=record.statement,
                invalidated_at=audit.transitioned_at if audit is not None else None,
                decided_by=audit.actor if audit is not None else None,
                justification=audit.justification if audit is not None else None,
                formatted=format_graveyard_entry(record, audit),
            )
        )
    return entries


def format_graveyard_line(entry: GraveyardEntry) -> str:
    return f"id={entry.knowledge_record_id}\n  {entry.formatted}"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.graveyard",
        description=(
            "Gate 5 — list invalidated conclusions for an account/EA "
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
        "--db",
        default=DEFAULT_KNOWLEDGE_DB_PATH,
        help=f"knowledge.db path (default: {DEFAULT_KNOWLEDGE_DB_PATH})",
    )
    p.add_argument("--limit", type=int, default=100, help="Max rows (default 100)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = KnowledgeRepository(args.db)
    profile = resolve_account(repo, args.account)
    if profile is None:
        print(f"No EA profile matching account={args.account!r}.", file=sys.stderr)
        return 0
    rows = list_graveyard(
        repository=repo,
        ea_profile_id=profile.id,
        limit=args.limit,
    )
    if not rows:
        print("No invalidated conclusions.")
        return 0
    print(f"{len(rows)} invalidated conclusion(s) for ea_key={profile.ea_key}:\n")
    for i, entry in enumerate(rows, start=1):
        print(f"[{i}] {format_graveyard_line(entry)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

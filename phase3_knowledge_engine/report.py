"""Phase 3 Block 6 — technical report of supported conclusions (presentation only).

Formats Knowledge-state records into a readable report. Matches the intent of
the documented (unimplemented) ``GET /query/supported-conclusions`` contract
entry. Does not change validation state, promote records, or enable the
feature flag.

Examples::

    python -m phase3_knowledge_engine.report
    python -m phase3_knowledge_engine.report --ea london-scalper
"""

from __future__ import annotations

import argparse
import sys
from uuid import UUID

from phase3_knowledge_engine.config import DEFAULT_KNOWLEDGE_DB_PATH
from phase3_knowledge_engine.domain.entities import EAKnowledgeProfile, KnowledgeRecord
from phase3_knowledge_engine.domain.ports.repository import KnowledgeRepositoryPort
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


def _fmt_date(value) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _fmt_datetime(value) -> str:
    if value is None:
        return ""
    return value.isoformat()


def _format_conclusion(
    record: KnowledgeRecord,
    profile: EAKnowledgeProfile | None,
) -> str:
    if profile is None:
        ea_line = (
            f"EA: (profile {record.ea_profile_id} not found)"
        )
    else:
        ea_line = (
            f"EA: ea_key={profile.ea_key}  name={profile.name}  "
            f"version={profile.version}"
        )
    return "\n".join(
        [
            f"Statement: {record.statement}",
            ea_line,
            f"confidence_score: {record.confidence_score}",
            f"evidence_count: {record.evidence_count}",
            f"sample_size: {record.sample_size}",
            f"date_range_start: {_fmt_date(record.date_range_start)}",
            f"date_range_end: {_fmt_date(record.date_range_end)}",
            f"last_reviewed_at: {_fmt_datetime(record.last_reviewed_at)}",
            f"reviewed_by: {record.reviewed_by or ''}",
        ]
    )


def build_technical_report(
    ea_profile_id: UUID | None = None,
    *,
    repository: KnowledgeRepositoryPort,
    limit: int = 100,
) -> str:
    """Build a presentation-only report of KNOWLEDGE-state records.

    Uses ``list_knowledge_records_by_state(ValidationState.KNOWLEDGE, ...)``.
    Empty result returns an explanatory message (not an error).
    """
    records = repository.list_knowledge_records_by_state(
        ValidationState.KNOWLEDGE,
        ea_profile_id=ea_profile_id,
        limit=limit,
    )
    if not records:
        if ea_profile_id is not None:
            return (
                "No supported conclusions (validation_state=knowledge) "
                f"for ea_profile_id={ea_profile_id}."
            )
        return "No supported conclusions (validation_state=knowledge)."

    sections: list[str] = [
        f"Technical report — {len(records)} supported conclusion(s) "
        f"(validation_state=knowledge)",
        "",
    ]
    for i, record in enumerate(records, start=1):
        profile = repository.get_ea_profile(record.ea_profile_id)
        sections.append(f"--- [{i}] id={record.id} ---")
        sections.append(_format_conclusion(record, profile))
        sections.append("")
    return "\n".join(sections).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.report",
        description=(
            "Phase 3 Block 6 — technical report of supported conclusions "
            "(presentation only; no state changes)."
        ),
    )
    p.add_argument(
        "--ea",
        default=None,
        metavar="EA_KEY",
        help="Optional ea_key filter (looked up in knowledge.db)",
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
    ea_profile_id: UUID | None = None
    if args.ea:
        profile = repo.get_ea_profile_by_ea_key(args.ea)
        if profile is None:
            print(f"No EA profile with ea_key={args.ea!r}.", file=sys.stderr)
            return 1
        ea_profile_id = profile.id
    text = build_technical_report(
        ea_profile_id,
        repository=repo,
        limit=args.limit,
    )
    print(text, end="" if text.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

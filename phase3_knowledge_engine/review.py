"""Standalone Phase 3 Block 3 review CLI — read-only visibility for humans.

Lists KnowledgeRecords waiting in a given validation state so a reviewer can
choose which record to act on next (e.g. call create_hypothesis separately).

Does not promote, transition, or enable PHASE3_KNOWLEDGE_ENGINE_ENABLED.

Examples::

    python -m phase3_knowledge_engine.review --state repeated_pattern
    python -m phase3_knowledge_engine.review --state repeated_pattern --ea london-scalper
"""

from __future__ import annotations

import argparse
import sys

from phase3_knowledge_engine.config import DEFAULT_KNOWLEDGE_DB_PATH
from phase3_knowledge_engine.domain.entities import KnowledgeRecord
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository


def _parse_state(raw: str) -> ValidationState:
    key = raw.strip().lower().replace("-", "_")
    try:
        return ValidationState(key)
    except ValueError as e:
        valid = ", ".join(s.value for s in ValidationState)
        raise argparse.ArgumentTypeError(
            f"Unknown state {raw!r}. Valid: {valid}"
        ) from e


def format_record_line(record: KnowledgeRecord) -> str:
    created = record.created_at.isoformat() if record.created_at else ""
    return (
        f"id={record.id}  "
        f"ea_profile_id={record.ea_profile_id}  "
        f"evidence_count={record.evidence_count}  "
        f"context_signature={record.context_signature or ''}  "
        f"created_at={created}\n"
        f"  statement: {record.statement}"
    )


def list_for_review(
    *,
    db_path: str,
    state: ValidationState,
    ea_key: str | None,
    limit: int,
) -> list[KnowledgeRecord]:
    repo = KnowledgeRepository(db_path)
    ea_profile_id = None
    if ea_key:
        profile = repo.get_ea_profile_by_ea_key(ea_key)
        if profile is None:
            print(f"No EA profile with ea_key={ea_key!r}.", file=sys.stderr)
            return []
        ea_profile_id = profile.id
    return repo.list_knowledge_records_by_state(
        state, ea_profile_id=ea_profile_id, limit=limit
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.review",
        description=(
            "Phase 3 Block 3 — list knowledge records by validation state "
            "(read-only; no automatic promotion)."
        ),
    )
    p.add_argument(
        "--state",
        required=True,
        type=_parse_state,
        help="Validation state to list (e.g. repeated_pattern, raw_observation)",
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
    rows = list_for_review(
        db_path=args.db,
        state=args.state,
        ea_key=args.ea,
        limit=args.limit,
    )
    if not rows:
        print(f"No knowledge records in state={args.state.value}.")
        return 0
    print(f"{len(rows)} record(s) in state={args.state.value} (oldest updated_at first):\n")
    for i, record in enumerate(rows, start=1):
        print(f"[{i}] {format_record_line(record)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

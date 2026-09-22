"""CLI for the static Educador glossary (Stage 1 — no HTTP, no AI).

Examples::

    python -m education.glossary --concept spread
    python -m education.glossary --list
"""

from __future__ import annotations

import argparse
import json
import sys

from education.catalog import get_explanation, list_concept_ids


def _serialize(explanation) -> dict:
    return {
        "id": explanation.id,
        "title": explanation.title,
        "definition": explanation.definition,
        "example": explanation.example,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m education.glossary",
        description=(
            "Revolution AI Stage 1 — inspect the static Educador glossary. "
            "No AI, no HTTP, no account data."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--concept",
        metavar="ID",
        help="Stable concept id (e.g. spread). Unknown ids exit 1 with no body.",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="Print the closed set of concept ids and titles.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.list:
        rows = []
        for concept_id in list_concept_ids():
            item = get_explanation(concept_id)
            if item is None:
                continue
            rows.append({"id": item.id, "title": item.title})
        print(json.dumps({"concepts": rows}, ensure_ascii=False, indent=2))
        return 0

    explanation = get_explanation(args.concept)
    if explanation is None:
        known = ", ".join(list_concept_ids())
        print(f"unknown concept id: {args.concept!r}", file=sys.stderr)
        print(f"known ids: {known}", file=sys.stderr)
        return 1

    print(json.dumps(_serialize(explanation), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

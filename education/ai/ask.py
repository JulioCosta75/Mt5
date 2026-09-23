"""CLI for Educador Stage 2. Never fabricates an answer without a key.

Examples::

    python -m education.ai.ask --concept spread --question "O que é o spread?" \\
        --user alice --tier free
"""

from __future__ import annotations

import argparse
import json
import sys

from ai_usage.application.services import UsageService, route_model
from ai_usage.config import DEFAULT_AI_USAGE_DB_PATH
from ai_usage.domain.entities import TIERS
from ai_usage.infrastructure.repositories import UsageRepository
from education.ai.clients import AnthropicLLMClient, LLMClientError, MissingAPIKeyError
from education.ai.service import answer_educador_question


def _serialize(answer) -> dict:
    return {
        "text": answer.text,
        "limit_reached": answer.limit_reached,
        "blocked": answer.blocked,
        "concept_id": answer.concept_id,
        "model": answer.model,
        "input_tokens": answer.input_tokens,
        "output_tokens": answer.output_tokens,
        "usage_id": str(answer.usage_id) if answer.usage_id else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m education.ai.ask",
        description=(
            "Educador Stage 2 — budget-guarded question. "
            "Requires ANTHROPIC_API_KEY for a real call. Never fabricates."
        ),
    )
    parser.add_argument("--question", required=True, help="User question (generic education only)")
    parser.add_argument(
        "--concept",
        default=None,
        metavar="ID",
        help="Optional glossary id to ground the answer (e.g. spread)",
    )
    parser.add_argument("--user", required=True, help="user_id for the budget guard")
    parser.add_argument("--tier", required=True, choices=sorted(TIERS))
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model short name. Default haiku; sonnet only if requested.",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_AI_USAGE_DB_PATH,
        help=f"ai_usage.db path (default: {DEFAULT_AI_USAGE_DB_PATH})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    usage = UsageService(UsageRepository(args.db))
    client = AnthropicLLMClient(model=route_model(args.model))
    try:
        answer = answer_educador_question(
            user_id=args.user,
            tier=args.tier,
            question=args.question,
            client=client,
            usage=usage,
            concept_id=args.concept,
            requested_model=args.model,
        )
    except MissingAPIKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except LLMClientError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(_serialize(answer), ensure_ascii=False, indent=2))
    if answer.limit_reached:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

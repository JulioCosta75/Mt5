"""CLI for the isolated AI usage / budget guard (no LLM, no HTTP).

Examples::

    python -m ai_usage.usage record --user alice --mode educador --model haiku \\
        --input-tokens 1000 --output-tokens 200
    python -m ai_usage.usage quota --user alice --tier free
    python -m ai_usage.usage budget
    python -m ai_usage.usage rate --user alice
    python -m ai_usage.usage route --requested sonnet
    python -m ai_usage.usage list --user alice
"""

from __future__ import annotations

import argparse
import json
import sys

from ai_usage.application.services import UsageService, route_model
from ai_usage.config import DEFAULT_AI_USAGE_DB_PATH
from ai_usage.domain.entities import MODELS, MODES, TIERS
from ai_usage.domain.rules import UsageValidationError
from ai_usage.infrastructure.repositories import UsageRepository


def _serialize(record) -> dict:
    return {
        "id": str(record.id),
        "user_id": record.user_id,
        "mode": record.mode,
        "model": record.model,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "estimated_cost_usd": str(record.estimated_cost_usd),
        "occurred_at": record.occurred_at.isoformat(),
    }


def _service(db_path: str) -> UsageService:
    return UsageService(UsageRepository(db_path))


def cmd_record(args: argparse.Namespace) -> int:
    record = _service(args.db).record_usage(
        user_id=args.user,
        mode=args.mode,
        model=args.model,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
    )
    print(json.dumps(_serialize(record), indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    rows = _service(args.db).list_for_user(args.user)
    print(json.dumps({"usage": [_serialize(r) for r in rows]}, indent=2))
    return 0


def cmd_quota(args: argparse.Namespace) -> int:
    allowed = _service(args.db).check_quota(args.user, args.tier)
    print(json.dumps({"user_id": args.user, "tier": args.tier, "allowed": allowed}, indent=2))
    return 0 if allowed else 1


def cmd_budget(args: argparse.Namespace) -> int:
    allowed = _service(args.db).check_global_budget()
    print(json.dumps({"allowed": allowed}, indent=2))
    return 0 if allowed else 1


def cmd_rate(args: argparse.Namespace) -> int:
    allowed = _service(args.db).check_rate_limit(args.user)
    print(json.dumps({"user_id": args.user, "allowed": allowed}, indent=2))
    return 0 if allowed else 1


def cmd_route(args: argparse.Namespace) -> int:
    model = route_model(args.requested)
    print(json.dumps({"model": model, "requested": args.requested}, indent=2))
    return 0


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=DEFAULT_AI_USAGE_DB_PATH,
        help=f"ai_usage.db path (default: {DEFAULT_AI_USAGE_DB_PATH})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ai_usage.usage",
        description=(
            "Isolated AI usage and budget guard. Synthetic token counts only. "
            "No LLM, no HTTP, no API key."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    record_p = sub.add_parser("record", help="Append one synthetic usage row")
    _add_db(record_p)
    record_p.add_argument("--user", required=True)
    record_p.add_argument("--mode", required=True, choices=sorted(MODES))
    record_p.add_argument("--model", required=True, choices=sorted(MODELS))
    record_p.add_argument("--input-tokens", required=True, type=int)
    record_p.add_argument("--output-tokens", required=True, type=int)
    record_p.set_defaults(func=cmd_record)

    list_p = sub.add_parser("list", help="List this user's usage rows only")
    _add_db(list_p)
    list_p.add_argument("--user", required=True)
    list_p.set_defaults(func=cmd_list)

    quota_p = sub.add_parser("quota", help="Check this user's tier quota")
    _add_db(quota_p)
    quota_p.add_argument("--user", required=True)
    quota_p.add_argument("--tier", required=True, choices=sorted(TIERS))
    quota_p.set_defaults(func=cmd_quota)

    budget_p = sub.add_parser("budget", help="Check the app-wide daily/monthly ceiling")
    _add_db(budget_p)
    budget_p.set_defaults(func=cmd_budget)

    rate_p = sub.add_parser("rate", help="Check this user's per-minute/hour call cap")
    _add_db(rate_p)
    rate_p.add_argument("--user", required=True)
    rate_p.set_defaults(func=cmd_rate)

    route_p = sub.add_parser("route", help="Resolve haiku/sonnet (default haiku)")
    route_p.add_argument("--requested", default=None)
    route_p.set_defaults(func=cmd_route)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except UsageValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

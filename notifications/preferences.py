"""CLI for notification preferences (Stage 1 — no HTTP, no delivery).

Examples::

    python -m notifications.preferences list --user alice --account MT5-1111
    python -m notifications.preferences create --user alice --account MT5-1111 \\
        --alert-type risk_drawdown --priority high --frequency immediate \\
        --channel telegram

Does not enable ATLAS_NOTIFICATIONS_ENABLED. Does not touch Phase 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from notifications.application.services import PreferenceService
from notifications.config import DEFAULT_NOTIFICATIONS_DB_PATH
from notifications.domain.entities import ALERT_TYPES, CHANNEL_LABELS, FREQUENCIES, PRIORITIES
from notifications.domain.rules import PreferenceValidationError
from notifications.infrastructure.repositories import (
    NotificationPreferenceRepository,
    PreferenceNotFoundError,
)


def _serialize(pref) -> dict:
    return {
        "id": str(pref.id),
        "user_id": pref.user_id,
        "account_id": pref.account_id,
        "alert_type": pref.alert_type,
        "priority": pref.priority,
        "frequency": pref.frequency,
        "channel": pref.channel,
        "quiet_hours_start": pref.quiet_hours_start,
        "quiet_hours_end": pref.quiet_hours_end,
        "active": pref.active,
        "created_at": pref.created_at.isoformat() if pref.created_at else None,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
    }


def _service(db_path: str) -> PreferenceService:
    return PreferenceService(NotificationPreferenceRepository(db_path))


def cmd_list(args: argparse.Namespace) -> int:
    rows = _service(args.db).list_for_account(args.user, args.account)
    print(json.dumps({"preferences": [_serialize(r) for r in rows]}, indent=2))
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    pref = _service(args.db).create(
        actor=args.user,
        user_id=args.user,
        account_id=args.account,
        alert_type=args.alert_type,
        priority=args.priority,
        frequency=args.frequency,
        channel=args.channel,
        quiet_hours_start=args.quiet_hours_start,
        quiet_hours_end=args.quiet_hours_end,
        active=bool(args.active),
    )
    print(json.dumps(_serialize(pref), indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    changes = {}
    if args.alert_type is not None:
        changes["alert_type"] = args.alert_type
    if args.priority is not None:
        changes["priority"] = args.priority
    if args.frequency is not None:
        changes["frequency"] = args.frequency
    if args.channel is not None:
        changes["channel"] = args.channel
    if args.quiet_hours_start is not None or args.quiet_hours_end is not None:
        changes["quiet_hours_start"] = args.quiet_hours_start
        changes["quiet_hours_end"] = args.quiet_hours_end
    if args.active is not None:
        changes["active"] = args.active
    pref = _service(args.db).update(
        actor=args.user,
        user_id=args.user,
        account_id=args.account,
        preference_id=UUID(args.id),
        **changes,
    )
    print(json.dumps(_serialize(pref), indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    _service(args.db).delete(
        actor=args.user,
        user_id=args.user,
        account_id=args.account,
        preference_id=UUID(args.id),
    )
    print(json.dumps({"deleted": args.id}))
    return 0


def _add_scope(p: argparse.ArgumentParser) -> None:
    p.add_argument("--user", required=True, help="user_id that owns the preference")
    p.add_argument("--account", required=True, help="MT5-{login} account id")
    p.add_argument(
        "--db",
        default=DEFAULT_NOTIFICATIONS_DB_PATH,
        help=f"notifications.db path (default: {DEFAULT_NOTIFICATIONS_DB_PATH})",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m notifications.preferences",
        description=(
            "Stage 1 — isolated notification preference CLI. "
            "No delivery, no channels, flag untouched."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List this user's preferences for one account")
    _add_scope(list_p)
    list_p.set_defaults(func=cmd_list)

    create_p = sub.add_parser("create", help="Explicitly create one preference (active=false unless --active)")
    _add_scope(create_p)
    create_p.add_argument("--alert-type", required=True, choices=sorted(ALERT_TYPES))
    create_p.add_argument("--priority", required=True, choices=sorted(PRIORITIES))
    create_p.add_argument("--frequency", required=True, choices=sorted(FREQUENCIES))
    create_p.add_argument("--channel", required=True, choices=sorted(CHANNEL_LABELS))
    create_p.add_argument("--quiet-hours-start", default=None)
    create_p.add_argument("--quiet-hours-end", default=None)
    create_p.add_argument(
        "--active",
        action="store_true",
        default=False,
        help="Explicitly activate this preference (off unless passed)",
    )
    create_p.set_defaults(func=cmd_create)

    update_p = sub.add_parser("update", help="Update one of this user's preferences")
    _add_scope(update_p)
    update_p.add_argument("--id", required=True)
    update_p.add_argument("--alert-type", default=None, choices=sorted(ALERT_TYPES))
    update_p.add_argument("--priority", default=None, choices=sorted(PRIORITIES))
    update_p.add_argument("--frequency", default=None, choices=sorted(FREQUENCIES))
    update_p.add_argument("--channel", default=None, choices=sorted(CHANNEL_LABELS))
    update_p.add_argument("--quiet-hours-start", default=None)
    update_p.add_argument("--quiet-hours-end", default=None)
    active = update_p.add_mutually_exclusive_group()
    active.add_argument("--active", dest="active", action="store_true", default=None)
    active.add_argument("--inactive", dest="active", action="store_false")
    update_p.set_defaults(func=cmd_update)

    delete_p = sub.add_parser("delete", help="Delete one of this user's preferences")
    _add_scope(delete_p)
    delete_p.add_argument("--id", required=True)
    delete_p.set_defaults(func=cmd_delete)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (PreferenceValidationError, PreferenceNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""One-shot live DEMO probe: getMe/getUpdates + a single sendMessage.

Never prints TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID. Output is sanitized.
Does not talk to MT5. Does not place orders.

Usage (after TELEGRAM_BOT_TOKEN is injected as a Cursor Runtime Secret):

    APP_MODE=demo TELEGRAM_TRANSPORT=http python3 -m telegram_demo_outbound.live_probe
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from telegram_demo_outbound.config import (
    require_bot_token,
    require_demo_app_mode,
)
from telegram_demo_outbound.constants import CHAT_ID_ENV, REQUIRED_PREFIX
from telegram_demo_outbound.errors import (
    FailClosedError,
    MissingAllowlistError,
    MissingTokenError,
)
from telegram_demo_outbound.redact import redact_text, sanitize_telegram_json
from telegram_demo_outbound.transport import TelegramHttpTransport, UrlLibHttpClient

REPORT_PATH = Path("telegram_demo_outbound/reports/live_probe_sanitized.json")
LIVE_TEXT = f"{REQUIRED_PREFIX} Ligação Telegram SUS-010 confirmada"


def _raw_private_chat_ids(body: str) -> list[str]:
    """Extract private chat ids from an unsanitized getUpdates body in-process.

    Values are used only to populate the in-memory allowlist and are never printed.
    """
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return []
    result = payload.get("result")
    if not isinstance(result, list):
        return []
    found: list[str] = []
    seen: set[str] = set()
    for update in result:
        if not isinstance(update, dict):
            continue
        message = update.get("message") or update.get("edited_message") or {}
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        if not isinstance(chat, dict):
            continue
        if chat.get("type") == "private" and chat.get("id") is not None:
            key = str(chat.get("id"))
            if key not in seen:
                seen.add(key)
                found.append(key)
        member = update.get("my_chat_member") or {}
        if isinstance(member, dict):
            mchat = member.get("chat") or {}
            if (
                isinstance(mchat, dict)
                and mchat.get("type") == "private"
                and mchat.get("id") is not None
            ):
                key = str(mchat.get("id"))
                if key not in seen:
                    seen.add(key)
                    found.append(key)
    return found


def resolve_allowlist(
    env: dict[str, str],
    get_updates_status: int,
    get_updates_raw_body: str,
    get_updates_sanitized: dict,
) -> tuple[frozenset[str], dict]:
    discovered = _raw_private_chat_ids(get_updates_raw_body)
    configured = (env.get(CHAT_ID_ENV) or "").strip()
    note = {
        "get_updates_http_status": get_updates_status,
        "get_updates_ok": bool(get_updates_sanitized.get("ok")),
        "private_chats_in_updates": len(discovered),
        "TELEGRAM_CHAT_ID_configured": bool(configured),
        "chat_id_matched_updates": False,
        "resolution": "",
    }
    if configured:
        if configured in discovered:
            note["chat_id_matched_updates"] = True
            note["resolution"] = "env_chat_id_matched_getUpdates"
            return frozenset({configured}), note
        if discovered:
            note["resolution"] = "env_chat_id_not_in_getUpdates"
            raise MissingAllowlistError(
                "TELEGRAM_CHAT_ID did not match any private chat in getUpdates"
            )
        # getUpdates empty: user may have started the bot earlier; still use env.
        note["resolution"] = "env_chat_id_used_getUpdates_empty"
        return frozenset({configured}), note
    if len(discovered) == 1:
        note["resolution"] = "single_private_chat_from_getUpdates"
        note["chat_id_matched_updates"] = True
        return frozenset({discovered[0]}), note
    if len(discovered) == 0:
        note["resolution"] = "no_private_chat_in_getUpdates"
        raise MissingAllowlistError(
            "getUpdates returned no private chat; send /start to the bot, "
            "or set TELEGRAM_CHAT_ID as a Cursor Runtime Secret"
        )
    note["resolution"] = "multiple_private_chats"
    raise MissingAllowlistError(
        "getUpdates returned multiple private chats; set TELEGRAM_CHAT_ID "
        "as a Cursor Runtime Secret"
    )


def run_live_probe(env: dict[str, str] | None = None) -> dict:
    source = dict(os.environ if env is None else env)
    report: dict = {
        "probe": "telegram_demo_outbound.live_probe",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "app_mode_is_demo": False,
        "getMe": None,
        "getUpdates": None,
        "sendMessage": None,
        "error": None,
    }
    try:
        require_demo_app_mode(source)
        report["app_mode_is_demo"] = True
        token = require_bot_token(source)
    except (FailClosedError, MissingTokenError) as exc:
        report["error"] = str(exc)
        return report

    http = UrlLibHttpClient()
    # Temporary allowlist of empty set; send is not called until resolved.
    bootstrap = TelegramHttpTransport(
        token=token,
        allowlist=frozenset({"0"}),
        app_mode=source.get("APP_MODE"),
        http=http,
    )

    get_me_status, get_me_body = bootstrap.get_me()
    report["getMe"] = {
        "http_status": get_me_status,
        "body": get_me_body,
        "token_accepted": get_me_status == 200 and bool(get_me_body.get("ok")),
        "is_bot": bool((get_me_body.get("result") or {}).get("is_bot"))
        if isinstance(get_me_body.get("result"), dict)
        else False,
        "username_present": bool((get_me_body.get("result") or {}).get("username"))
        if isinstance(get_me_body.get("result"), dict)
        else False,
    }
    if not report["getMe"]["token_accepted"]:
        report["error"] = "getMe did not accept the token (HTTP or ok field)"
        return report

    # Call getUpdates at HTTP layer so we can resolve chat ids in-process
    # without printing them. The sanitized copy is what we persist.
    raw_updates = http.post(
        f"https://api.telegram.org/bot{token}/getUpdates",
        {"timeout": "25", "limit": "100"},
        35.0,
    )
    try:
        updates_parsed = json.loads(raw_updates.body) if raw_updates.body else {}
    except json.JSONDecodeError:
        updates_parsed = {"ok": False, "description": "non-json-body"}
    updates_sanitized = sanitize_telegram_json(
        updates_parsed,
        secrets=(token, *([source[CHAT_ID_ENV]] if source.get(CHAT_ID_ENV) else [])),
    )
    report["getUpdates"] = {
        "http_status": raw_updates.status,
        "body": updates_sanitized,
        "ok": bool(updates_sanitized.get("ok")) if isinstance(updates_sanitized, dict) else False,
    }

    try:
        allowlist, resolution = resolve_allowlist(
            source,
            raw_updates.status,
            raw_updates.body,
            updates_sanitized if isinstance(updates_sanitized, dict) else {},
        )
    except MissingAllowlistError as exc:
        report["error"] = str(exc)
        report["getUpdates"]["resolution"] = str(exc)
        result = (
            (updates_sanitized or {}).get("result")
            if isinstance(updates_sanitized, dict)
            else None
        )
        report["getUpdates"]["private_chats_in_updates"] = 0
        report["getUpdates"]["pending_updates"] = (
            len(result) if isinstance(result, list) else None
        )
        report["getUpdates"]["TELEGRAM_CHAT_ID_configured"] = bool(
            (source.get(CHAT_ID_ENV) or "").strip()
        )
        report["getUpdates"]["chat_id_matched_updates"] = False
        return report

    report["getUpdates"]["resolution"] = resolution["resolution"]
    report["getUpdates"]["private_chats_in_updates"] = resolution["private_chats_in_updates"]
    report["getUpdates"]["TELEGRAM_CHAT_ID_configured"] = resolution["TELEGRAM_CHAT_ID_configured"]
    report["getUpdates"]["chat_id_matched_updates"] = resolution["chat_id_matched_updates"]

    sender = TelegramHttpTransport(
        token=token,
        allowlist=allowlist,
        app_mode=source.get("APP_MODE"),
        http=http,
    )
    chat_id = next(iter(allowlist))
    send_result = sender.send_message(chat_id, LIVE_TEXT)
    report["sendMessage"] = {
        "http_status": send_result.status,
        "ok": send_result.ok,
        "provider_message_id": send_result.provider_message_id,
        "body": send_result.sanitized_body,
        "text_startswith_required_prefix": LIVE_TEXT.startswith(REQUIRED_PREFIX),
    }
    # Redact anything that slipped through.
    dumped = json.dumps(report)
    dumped = redact_text(dumped, (token, chat_id))
    return json.loads(dumped)


def public_summary(report: dict) -> dict:
    """Fields safe to print or put on a PR. No token, no chat_id, no personal names."""
    get_me = report.get("getMe") or {}
    get_me_body = get_me.get("body") if isinstance(get_me.get("body"), dict) else {}
    get_me_result = (
        get_me_body.get("result") if isinstance(get_me_body.get("result"), dict) else {}
    )
    updates = report.get("getUpdates") or {}
    send = report.get("sendMessage") or {}
    send_body = send.get("body") if isinstance(send.get("body"), dict) else {}
    send_result = send_body.get("result") if isinstance(send_body.get("result"), dict) else {}
    chat = send_result.get("chat") if isinstance(send_result.get("chat"), dict) else {}
    return {
        "probe": report.get("probe"),
        "ran_at": report.get("ran_at"),
        "app_mode_is_demo": report.get("app_mode_is_demo"),
        "error": report.get("error"),
        "getMe": {
            "http_status": get_me.get("http_status"),
            "ok": get_me_body.get("ok"),
            "token_accepted": get_me.get("token_accepted"),
            "is_bot": get_me.get("is_bot"),
            "username_present": get_me.get("username_present"),
            "bot_username": get_me_result.get("username"),
        },
        "getUpdates": {
            "http_status": updates.get("http_status"),
            "ok": updates.get("ok"),
            "resolution": updates.get("resolution"),
            "private_chats_in_updates": updates.get("private_chats_in_updates"),
            "pending_updates": updates.get("pending_updates"),
            "TELEGRAM_CHAT_ID_configured": updates.get("TELEGRAM_CHAT_ID_configured"),
            "chat_id_matched_updates": updates.get("chat_id_matched_updates"),
        },
        "sendMessage": {
            "http_status": send.get("http_status"),
            "ok": send.get("ok"),
            "telegram_ok": send_body.get("ok"),
            "provider_message_id": send.get("provider_message_id"),
            "message_id": send_result.get("message_id"),
            "date": send_result.get("date"),
            "chat_type": chat.get("type"),
            "chat_id": "[REDACTED_CHAT_ID]",
            "text": send_result.get("text"),
            "text_startswith_required_prefix": send.get(
                "text_startswith_required_prefix"
            ),
        },
    }


def main() -> int:
    report = run_live_probe()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = public_summary(report)
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if report.get("error"):
        return 2
    send = report.get("sendMessage") or {}
    if send.get("ok") and send.get("http_status") == 200:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

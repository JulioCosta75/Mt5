"""Problem-report diagnostics + local SQLite registry + Resend email.

Collection and registration only — never auto-remediation, never credentials.
Uses Resend's HTTP API via httpx (no extra Python package).

Env:
  RESEND_API_KEY          — required to email (Julio creates the Resend account)
  REPORT_PROBLEM_TO       — default juliopdcosta@gmail.com
  REPORT_PROBLEM_FROM     — verified sender, e.g. "Sr. Atlas <onboarding@resend.dev>"
  ATLAS_SQLITE_PATH       — SQLite file for problem_reports table (shared atlas.db OK)
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from problem_report_store import ProblemReportStore

logger = logging.getLogger("problem_report")

# Substrings that mark a dict key / env name as secret (case-insensitive).
_SECRET_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|bearer|"
    r"credential|private[_-]?key|mt5_login|login$)",
    re.IGNORECASE,
)

DEFAULT_TO = "juliopdcosta@gmail.com"
DEFAULT_FROM = "Sr. Atlas <onboarding@resend.dev>"
USER_FACING_FAIL = (
    "could not send by email — try again later or contact us directly."
)
NOT_CONFIGURED_FAIL = (
    "email sending isn't configured on this Atlas yet. "
    "Contact Forge Factory Lab directly."
)


class ReportSendError(Exception):
    """Raised when the email cannot be sent. ``user_message`` is safe to show."""

    def __init__(self, user_message: str, *, status_code: int = 503, report_id: int | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.status_code = status_code
        self.report_id = report_id


def _is_secret_key(key: str) -> bool:
    return bool(_SECRET_KEY_RE.search(str(key)))


def sanitize(value: Any, *, _depth: int = 0) -> Any:
    """Recursively drop secret-looking keys and redact obvious secret strings."""
    if _depth > 12:
        return "<truncated>"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _is_secret_key(k):
                continue
            out[str(k)] = sanitize(v, _depth=_depth + 1)
        return out
    if isinstance(value, list):
        return [sanitize(v, _depth=_depth + 1) for v in value[:200]]
    if isinstance(value, str):
        if len(value) >= 24 and re.fullmatch(r"[A-Za-z0-9_\-\.=]+", value):
            if value.startswith(("re_", "sk_", "Bearer", "ghp_")):
                return "<redacted>"
        return value
    return value


def _tail_log_file(path: Path, max_lines: int = 80) -> list[str]:
    try:
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        cleaned = []
        for line in lines[-max_lines:]:
            if _SECRET_KEY_RE.search(line) and ("=" in line or ":" in line):
                cleaned.append("<line redacted — possible secret>")
            else:
                cleaned.append(line[:500])
        return cleaned
    except OSError as e:
        return [f"<could not read {path.name}: {e}>"]


def collect_log_tails() -> dict[str, list[str]]:
    """Best-effort recent log lines from common Atlas log locations."""
    candidates: list[Path] = []
    root = Path(__file__).resolve().parent
    candidates.extend(
        [
            root / "logs" / "backend.log",
            root / "logs" / "bridge.log",
            root / "logs" / "atlas.log",
            root.parent / "logs" / "backend.log",
            root.parent / "logs" / "bridge.log",
        ]
    )
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or ""
    if local:
        atlas = Path(local) / "Atlas" / "logs"
        candidates.extend(
            [
                atlas / "backend.log",
                atlas / "bridge.log",
                atlas / "atlas_launcher.log",
                atlas / "backend.err.log",
                atlas / "bridge.err.log",
            ]
        )

    out: dict[str, list[str]] = {}
    seen = set()
    for path in candidates:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            out[path.name] = _tail_log_file(path)
            if len(out) >= 4:
                break
    return out


def build_diagnostic_payload(health: dict, *, note: str | None = None) -> dict:
    """Assemble a sanitized diagnostic document from system health + logs."""
    bridge = health.get("bridge")
    bridge_safe = None
    if isinstance(bridge, dict):
        bridge_safe = sanitize(
            {
                "url_host": _safe_url_host(bridge.get("url")),
                "reachable": bridge.get("reachable"),
                "terminal_connected": bridge.get("terminal_connected"),
                "account_logged_in": bridge.get("account_logged_in"),
                "server": bridge.get("server"),
                "last_error": bridge.get("last_error"),
                "trade_allowed": bridge.get("trade_allowed"),
                "message": bridge.get("message"),
                "error": bridge.get("error"),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product": "Sr. Atlas",
        "kind": "problem_report",
        "no_auto_remediation": True,
        "mode": health.get("mode"),
        "version": health.get("version"),
        "build": sanitize(health.get("build") or {}),
        "server_time": health.get("server_time"),
        "store": sanitize(health.get("store") or {}),
        "bridge": bridge_safe,
        "recent_logs": collect_log_tails(),
    }
    if note and isinstance(note, str) and note.strip():
        payload["user_note"] = note.strip()[:1000]
    return sanitize(payload)


def _safe_url_host(url: Any) -> str | None:
    if not url or not isinstance(url, str):
        return None
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        host = p.hostname or ""
        port = f":{p.port}" if p.port else ""
        return f"{host}{port}" if host else None
    except Exception:  # noqa: BLE001
        return None


def format_report_text(payload: dict) -> str:
    return (
        "Sr. Atlas — automatic problem report\n"
        "(collection / registration only — no automatic remediation)\n"
        "============================================\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    )


def _guess_tester(explicit: str | None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip()[:120]
    for key in ("ATLAS_TESTER_NAME", "USERNAME", "USER"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val[:120]
    return None


async def send_problem_report(payload: dict) -> dict:
    """Send diagnostic email via Resend. Raises ReportSendError on failure."""
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    if not api_key:
        raise ReportSendError(NOT_CONFIGURED_FAIL, status_code=503)

    to_addr = (os.environ.get("REPORT_PROBLEM_TO") or DEFAULT_TO).strip()
    from_addr = (os.environ.get("REPORT_PROBLEM_FROM") or DEFAULT_FROM).strip()
    subject = (
        f"[Sr. Atlas] Problem report · "
        f"{payload.get('version') or '?'} · "
        f"{payload.get('generated_at') or ''}"
    )
    text_body = format_report_text(payload)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_addr,
                    "to": [to_addr],
                    "subject": subject,
                    "text": text_body,
                },
            )
    except httpx.HTTPError as e:
        logger.warning("Resend transport error: %s", e)
        raise ReportSendError(USER_FACING_FAIL, status_code=503) from e

    if resp.status_code >= 400:
        logger.warning(
            "Resend rejected report: status=%s body=%s",
            resp.status_code,
            (resp.text or "")[:300],
        )
        raise ReportSendError(USER_FACING_FAIL, status_code=503)

    data = {}
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "message": "Report saved and sent, thank you",
        "provider": "resend",
        "id": data.get("id"),
    }


async def submit_problem_report(
    health: dict,
    *,
    note: str | None = None,
    tester: str | None = None,
    store: ProblemReportStore | None = None,
) -> dict:
    """Persist diagnostic locally, then attempt email. Never auto-remediates.

    Always writes SQLite history first. Email success → user confirmation.
    Email failure → clear error that still acknowledges the local save —
    never claims the email was sent.
    """
    payload = build_diagnostic_payload(health, note=note)
    build = payload.get("build") if isinstance(payload.get("build"), dict) else {}
    registry = store or ProblemReportStore()
    report_id = registry.insert(
        tester=_guess_tester(tester),
        atlas_version=str(payload.get("version") or build.get("version") or "") or None,
        atlas_build=str(build.get("build") or "") or None,
        diagnostic=payload,
        email_status="pending",
    )

    try:
        email_result = await send_problem_report(payload)
    except ReportSendError as e:
        status = "not_configured" if e.user_message == NOT_CONFIGURED_FAIL else "failed"
        registry.update_email(
            report_id,
            email_status=status,
            email_error=e.user_message,
        )
        raise ReportSendError(
            f"Report saved locally (#{report_id}), but {e.user_message}",
            status_code=e.status_code,
            report_id=report_id,
        ) from e

    registry.update_email(
        report_id,
        email_status="sent",
        email_provider_id=email_result.get("id"),
    )
    return {
        "ok": True,
        "saved": True,
        "email_sent": True,
        "report_id": report_id,
        "message": email_result.get("message")
        or "Report saved and sent, thank you",
        "provider": email_result.get("provider"),
        "email_id": email_result.get("id"),
    }

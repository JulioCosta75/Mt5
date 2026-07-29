# Launch Blockers — Sr. Atlas

Standing rule (founder decision, 2026-07-29): no external trader/tester may
receive this product until every item below is resolved. "Worked once under
supervision" does not count as resolved.

## Installation experience requirement

Sr. Atlas must install and run like a normal end-user program. If reaching a
working state requires manually editing an external application's config
files (e.g. the MT5 terminal's `common.ini`), hunting through `%APPDATA%`
folders, or toggling settings not exposed anywhere in Sr. Atlas's own
installer or dashboard, that is itself a launch blocker — not just the
underlying technical bug. The installer and/or bridge must detect required
MT5 terminal settings (Algo Trading, external API access) and either
configure them automatically or guide the user through them in plain
language, inside the product itself.

## Current known blockers

1. **MT5 bridge connection reliability** (`mt5-bridge/mt5_service.py`).
   Root cause: `mt5.login()` breaks the IPC handshake in this environment
   regardless of terminal state; working pattern is `mt5.initialize()` only,
   relying on an already-authenticated terminal session. Minimal fix
   authorized 2026-07-29. **Not resolved**: the bridge still cannot
   authenticate a session from zero without a human first logging into the
   terminal manually — not acceptable for handing to another user, and not
   suitable for unattended operation. Needs root-cause fix for why
   `mt5.login()` itself fails, not just a workaround around it.
2. **Phase 3 atomicity fix** — state-transition + audit-trail atomicity
   (`fix/phase3-atomic-transition-audit-20260727`), in progress.
3. **`knowledge.db` / `*.db` missing from `.gitignore`.**

# SUS-010 — Telegram DEMO outbound bridge (isolated)

This package is a **standalone outbound notifier**. It is **not** imported by
Production Phase 2 (`backend/`), the MT5 bridge, the installer, the frontend,
or the Phase 3 Knowledge Engine.

It does **not** connect to MT5, does **not** create or modify an EA, and does
**not** send trading orders.

## Safety rules

- Default transport is **mock** (`TELEGRAM_TRANSPORT` unset or `mock`).
- Real Telegram HTTP runs only when **both** are true:
  - `APP_MODE` is exactly `demo` (any other value, including absent/empty/`real`, **fail-closed**)
  - `TELEGRAM_TRANSPORT=http`
- Allowlist: only the validated `TELEGRAM_CHAT_ID` (Júlio) may receive messages.
- Every message starts with `[DEMO — TOKEN PROVISÓRIO]`.
- `TELEGRAM_BOT_TOKEN` is read from the process environment (Cursor **Runtime Secret**).
  Never commit it, never paste it in chat, never print it.
- Durable SQLite outbox with retry + `event_id` deduplication.
- Client-side rate limit aligned with Telegram Bot API (≈1 msg/s per chat, 30/s global).

## Tests (no network)

From the repository root, one command:

```bash
python3 telegram_demo_outbound/run_tests.py
```

The runner prints `PASS` / `FAILED` per scenario. It uses an in-memory mock of
the Telegram HTTP endpoint.

## Live probe (one real message, once)

Júlio: paste `TELEGRAM_BOT_TOKEN` into the Cursor Cloud **Runtime Secret** field
(Cloud Agents → Secrets → type **Runtime Secret**). Never paste it in this
repository or in the agent chat.

Then, after sending `/start` to the bot in Telegram (so `getUpdates` can see
the chat), run:

```bash
APP_MODE=demo TELEGRAM_TRANSPORT=http python3 -m telegram_demo_outbound.live_probe
```

The probe calls `getMe` and `getUpdates`, then sends **one** message that starts
with `[DEMO — TOKEN PROVISÓRIO]`. stdout and
`telegram_demo_outbound/reports/live_probe_sanitized.json` record HTTP status
and a **sanitized** body (token and chat_id redacted).

Optional: also set `TELEGRAM_CHAT_ID` as a Runtime Secret. If unset, the probe
uses the single private chat found in `getUpdates`.

## Synthetic events in this delivery

`telegram_demo_outbound/demo_payloads.py` contains labelled synthetic data:

- startup
- order_created (all required fields)
- daily_summary (all required fields)

These are **not** live trading events.

## Isolation

Do not import this package from `backend/server.py` or `mt5-bridge/` until a
later delivery is explicitly authorized.

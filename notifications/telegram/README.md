# Notifications Stage 2a — isolated Telegram adapter

> **ISOLATION WARNING**
>
> This submodule is **not integrated** with Phase 2 production runtime.
> Do **not** import it from `backend/server.py`, the dashboard, MT5 Bridge,
> installer scripts, or n8n workflows.
>
> No HTTP routes. No frontend. No alert-engine delivery yet.
>
> Automated tests use `FakeTelegramClient` (zero network, no bot token).

## Polling

Atlas runs on the operator's local computer, not on a public server. Telegram
cannot push updates to a webhook URL. While Atlas is open it long-polls
`getUpdates` (`TelegramAdapter.get_updates(offset)`).

## Commands (one-way informational channel)

Only these are handled:

| Command | Effect |
|---------|--------|
| `/start <code>` | Consume a one-time linking code. Store `chat_id` against `(user_id, account_id)`. Never a phone number. |
| `/help` | Fixed instructions. |
| `/stop` | Deactivate Telegram preferences for the linked `(user_id, account_id)`. |

Anything else receives the fixed reply:

> Este canal é exclusivamente informativo. O Sr. Atlas não aceita instruções, decisões de investimento ou ordens de negociação pelo Telegram. Utilize o dashboard para gerir as suas preferências.

No AI interpretation. Nothing is forwarded to a decision component.

## Token

`TELEGRAM_BOT_TOKEN` is read from the environment only, inside HTTP methods.
It is never hardcoded and is scrubbed from error messages.

## Tests

```bash
python3 -m pytest notifications/tests notifications/telegram/tests -q
```

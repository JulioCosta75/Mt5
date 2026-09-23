"""Notifications Stage 1 — isolated preference and consent model.

> **ISOLATION WARNING**
>
> This module is **not integrated** with Phase 2 production runtime.
> Do **not** import it from `backend/server.py`, the dashboard, MT5 Bridge,
> installer scripts, or n8n workflows.
>
> Feature flag: `ATLAS_NOTIFICATIONS_ENABLED=false` (default)
>
> No Phase 2 wiring. Stage 1 has no delivery. Stage 2a Telegram lives in
> `notifications/telegram/` and is tested with `FakeTelegramClient` only.

## Purpose

Store explicit user consent to receive future notifications, scoped by
`(user_id, account_id)` where `account_id` is the Gate 5 / Phase 2
`MT5-{login}` identifier.

A preference row exists only because a user created it. `active` defaults
to false. There is no bulk-enable helper and no default-on state.

## Layout

```
notifications/
├── config.py                 # ATLAS_NOTIFICATIONS_ENABLED default OFF
├── domain/                   # entities + validation
├── application/services.py   # create/update/delete + audit
├── infrastructure/           # SQLite notifications.db
├── preferences.py            # CLI
├── telegram/                 # Stage 2a isolated adapter (polling, FakeTelegramClient)
└── tests/
```

## CLI

```bash
python -m notifications.preferences list --user alice --account MT5-1111 --db ./notifications.db
python -m notifications.preferences create --user alice --account MT5-1111 \\
    --alert-type risk_drawdown --priority high --frequency immediate --channel telegram
```

`--active` must be passed explicitly to store an active preference.

## Tests

```bash
python3 -m pytest notifications/tests notifications/telegram/tests -q
```

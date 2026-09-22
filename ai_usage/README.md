"""Isolated AI usage and budget guard.

> **ISOLATION WARNING**
>
> This module is **not integrated** with Phase 2 production runtime.
> Do **not** import it from `backend/server.py`, the dashboard, MT5 Bridge,
> installer scripts, n8n workflows, `phase3_knowledge_engine`,
> `notifications`, or `education`.
>
> No LLM call, no external API, no API key, no HTTP in this stage.
> Tests use synthetic token counts only.

## Purpose

Record estimated cost of future AI calls and refuse further work when a
per-user quota, a per-user rate limit, or the app-wide budget is already
spent. Fails closed.

## Layout

```
ai_usage/
├── pricing.json              # Haiku/Sonnet USD per million tokens
├── quotas.json               # Free/Pro + global ceilings + rate limits
├── domain/                   # AIUsageRecord + validation
├── application/services.py   # check_quota / check_global_budget / record_usage
├── infrastructure/           # SQLite ai_usage.db (append-only)
├── usage.py                  # CLI
└── tests/
```

Pricing and quota numbers are JSON, not Python constants. Override paths
with `ATLAS_AI_USAGE_PRICING_PATH` and `ATLAS_AI_USAGE_QUOTAS_PATH`.

## License tier (read-only pattern)

`check_quota(user_id, tier)` accepts the public `tier` values from
`backend/license.py` `public_state()`: `free` and `pro`. Aliases
`pro_active` → `pro`, `pro_expired`/`checking` → `free`. This package
does **not** import `license.py` (that module uses `httpx`).

## CLI

```bash
python -m ai_usage.usage record --user alice --mode educador --model haiku \\
    --input-tokens 1000 --output-tokens 200 --db ./ai_usage.db
python -m ai_usage.usage quota --user alice --tier free --db ./ai_usage.db
python -m ai_usage.usage budget --db ./ai_usage.db
python -m ai_usage.usage route --requested sonnet
```

## Tests

```bash
python3 -m pytest ai_usage/tests/ -q
```

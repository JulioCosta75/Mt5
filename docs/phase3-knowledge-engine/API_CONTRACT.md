# Phase 3 API Contract

Prefix: `/api/knowledge/v1`

Feature gate: `PHASE3_KNOWLEDGE_ENGINE_ENABLED=true` (default **off** → HTTP 404)

## Mounted read-only (Gate 5 Stage 2b)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | `{enabled: true}` when flag on; **404** when off |
| `GET` | `/insights?account_id=` | Level A/B insights for EAs with evidence on that account |
| `GET` | `/graveyard?account_id=` | Invalidated conclusions for those EAs |
| `GET` | `/correlation?account_id=&ea_a=&ea_b=` | Negative-day coincidence (explicit EA keys) |
| `GET` | `/ea-profiles?account_id=` | EA dossiers with evidence on that account (empty if none) |

No POST/write routes are mounted.

`account_id` on `insights` / `graveyard` / `ea-profiles` is the MT5 account stored on `evidence_items.account_id`. Only EA profiles with real evidence for that account are returned. Empty list when none. `correlation` still takes two explicit EA keys.

## EA Profiles (unmounted writes / by-id)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ea-profiles/{id}` | Get dossier by ID |
| `POST` | `/ea-profiles` | Register or update dossier |

## Evidence & Observations

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/observations` | Register raw observation + evidence |
| `GET` | `/ea-profiles/{id}/evidence` | List evidence for EA |

## Knowledge Records

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/records/{id}` | Get knowledge record |
| `POST` | `/records/{id}/hypothesis` | Explicit hypothesis creation |
| `POST` | `/records/{id}/transition` | Human-reviewed state transition |
| `GET` | `/records/{id}/audit` | Audit trail |

## Knowledge Queries (future)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/query/best-session?ea_key=` | Best session from validated knowledge |
| `GET` | `/query/loss-conditions?ea_key=` | Conditions linked to losses |
| `GET` | `/query/performance-drift?ea_key=` | Version performance changes |
| `GET` | `/query/testing-candidates` | EAs needing more evidence |
| `GET` | `/query/supported-conclusions` | Conclusions meeting evidence thresholds |
| `GET` | `/query/restriction-reason?ea_key=` | Why an EA was stopped/restricted |

## DTOs

Pydantic models in `phase3_knowledge_engine/api/contract.py`.

## Safety constraints (permanent)

- No endpoint may start/stop EAs.
- No endpoint may modify capital allocation.
- No automatic promotion to `Knowledge` without human review payload.
- No write path to Phase 2 mock or live trading controls.

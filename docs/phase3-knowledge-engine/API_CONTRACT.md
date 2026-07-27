# Phase 3 API Contract (Proposal — NOT ACTIVE)

> These endpoints are **not mounted** on `backend/server.py`.
> They document the future HTTP surface for integration after Phase 2 validation.

Prefix: `/api/knowledge/v1`

Feature gate: `PHASE3_KNOWLEDGE_ENGINE_ENABLED=true`

## EA Profiles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ea-profiles` | List all EA dossiers |
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

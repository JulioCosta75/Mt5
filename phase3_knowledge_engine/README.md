# Phase 3 — Knowledge Management Engine (Isolated Foundation)

> **ISOLATION WARNING**
>
> This module is **not integrated** with Phase 2 production runtime.
> Do **not** import it from `backend/server.py`, the dashboard, MT5 Bridge,
> installer scripts, or n8n workflows until the Phase 2 validation gate passes.
>
> Feature flag: `PHASE3_KNOWLEDGE_ENGINE_ENABLED=false` (default)

## Purpose

Transform trading results into **traceable, validated knowledge** using the lifecycle:

```
Data → Context → Hypothesis → Observation → Validation → Conclusion → Knowledge → Decision Support
```

Forge Factory Lab principle (codified in `domain/rules.py`):

> **Knowledge is not what happened. Knowledge is what survived validation.**

## Layout

```
phase3_knowledge_engine/
├── config.py              # feature flag OFF by default
├── domain/                # pure rules, entities, state machine
├── application/           # use-cases (orchestration)
├── infrastructure/        # SQLite knowledge.db
├── api/contract.py        # future REST contract (NOT mounted)
└── tests/                 # unit + lifecycle tests

docs/phase3-knowledge-engine/
├── ARCHITECTURE.md
├── DOMAIN_MODEL.md
├── DATABASE_SCHEMA.md
├── API_CONTRACT.md
├── VALIDATION_STATE_MODEL.md
├── CONFIDENCE_SCORING.md
├── INTEGRATION_ROADMAP.md
└── examples/
```

## Running tests

```bash
cd /path/to/repo
python3 -m pytest phase3_knowledge_engine/tests/ -q
```

## Database

Separate SQLite file: `knowledge.db` (never `atlas.db`).

Environment variables (optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PHASE3_KNOWLEDGE_ENGINE_ENABLED` | `false` | Master integration gate |
| `PHASE3_KNOWLEDGE_DB_PATH` | `knowledge.db` | SQLite path |
| `PHASE3_MIN_OBSERVATIONS_FOR_PATTERN` | `2` | RepeatedPattern threshold |
| `PHASE3_MIN_EVIDENCE_FOR_KNOWLEDGE` | `10` | Minimum evidence count for Knowledge promotion (Rule 6) |
| `PHASE3_MIN_SAMPLE_FOR_KNOWLEDGE` | `30` | Minimum sample size for Knowledge promotion (Rule 6) |

Knowledge promotion thresholds are defined in `config.py` and consumed by
`domain/rules.py` and `application/services.py`. Adjust via environment
variables at process start; human review and other Rule 6 criteria are unchanged.

## Status

Foundation only — **Phase 3 branch, no merge to `main`**.

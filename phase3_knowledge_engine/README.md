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
│   └── ports/             # repository & evidence-source contracts
├── application/           # use-cases (orchestration)
│   └── state_transition_service.py  # sole FSM entry point
├── infrastructure/        # SQLite knowledge.db
├── adapters/ingestion/    # EvidenceSourcePort (stub + MT5 bridge Gate 1)
├── ingest.py              # CLI: --file / --bridge-url (not wired to Phase 2)
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

## Gate 1 ingestion CLI (standalone)

```bash
# From bridge JSON/CSV export
python3 -m phase3_knowledge_engine.ingest --file deals.json --db ./knowledge.db

# Live bridge (read-only GET /deals — reuses backend/mt5_client.BridgeClient)
python3 -m phase3_knowledge_engine.ingest \
  --bridge-url http://127.0.0.1:8002 \
  --bridge-token "$MT5_BRIDGE_TOKEN" \
  --days 90 \
  --db ./knowledge.db
```

Does **not** flip `PHASE3_KNOWLEDGE_ENGINE_ENABLED`. Never writes to the bridge or Phase 2 backend.

## Block 3 review queue (read-only)

```bash
python3 -m phase3_knowledge_engine.review --state repeated_pattern --db ./knowledge.db
python3 -m phase3_knowledge_engine.review --state repeated_pattern --ea london-scalper
```

Lists pending `KnowledgeRecord`s for human action (e.g. decide which id to pass to
`create_hypothesis`). No automatic promotion.

## Block 4/5 — EA version change + quarantine

Service methods (not HTTP-mounted):

- `record_ea_version_change(...)` — mandatory non-empty `description`; sets
  `version` and status `quarantine`; appends `ChangeLogEntry`.
- `confirm_ea_version_safe(...)` — explicit human clearance only when status is
  `quarantine` → `active` (never automatic from evidence/confidence).
- `list_ea_profiles(status=...)` / `list_change_log_for_ea(...)` on the repository.

## Block 6 — technical report (supported conclusions)

```bash
python3 -m phase3_knowledge_engine.report --db ./knowledge.db
python3 -m phase3_knowledge_engine.report --ea london-scalper
```

Presentation-only formatting of `ValidationState.KNOWLEDGE` records (statement,
EA key/name/version, confidence, evidence/sample sizes, date range, review
metadata). No state changes or promotion.

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

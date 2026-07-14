# Phase 3 Database Schema — knowledge.db

SQLite only. **Separate from `atlas.db`.**

DDL source: `phase3_knowledge_engine/infrastructure/schema.sql`

## Tables

| Table | Purpose |
|-------|---------|
| `schema_meta` | Schema version tracking |
| `ea_profiles` | EA knowledge dossiers |
| `market_contexts` | Contextual envelopes |
| `evidence_items` | Trades, backtests, incidents (with provenance) |
| `knowledge_records` | Statements in validation lifecycle |
| `audit_trail` | Immutable transition history |
| `evidence_impacts` | How new evidence affected knowledge |
| `performance_metrics` | Period aggregates per EA |
| `change_log` | Version change history |

## Key indexes

- `evidence_items(ea_profile_id)`
- `evidence_items(source_system, external_id)` — unique when `external_id` set (dedup)
- `knowledge_records(ea_profile_id, validation_state)`
- `audit_trail(knowledge_record_id)`

## Design notes

- UUIDs stored as TEXT primary keys.
- JSON columns stored as TEXT (`*_json` suffix).
- Foreign keys enforced (`PRAGMA foreign_keys = ON`).
- `InvalidatedConclusion` rows are never deleted — only inserted/updated in place with terminal state.
- No shared tables with Phase 2.

## Migration strategy (future)

1. Bump `schema_meta.schema_version`.
2. Add numbered migration scripts under `phase3_knowledge_engine/infrastructure/migrations/`.
3. Run migrations only when `PHASE3_KNOWLEDGE_ENGINE_ENABLED=true` in staging.

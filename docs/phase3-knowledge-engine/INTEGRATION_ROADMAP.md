# Phase 3 Integration Roadmap

## Gate 0 — Current (this branch)

- [x] Isolated module `phase3_knowledge_engine/`
- [x] Documentation in `docs/phase3-knowledge-engine/`
- [x] `knowledge.db` schema
- [x] Domain rules + unit tests
- [x] Feature flag OFF
- [ ] Phase 2 fully validated on Windows VPS
- [ ] No merge to `main`

## Gate 1 — Read-only ingestion (staging)

- [x] Batch adapter: closed trades from MT5 bridge `GET /deals` → `EvidenceItem`
      (`adapters/ingestion/mt5_bridge_evidence_source.py`)
- [x] Standalone CLI: `python -m phase3_knowledge_engine.ingest --file …`
      or `--bridge-url` / `--bridge-token` (reuses `backend/mt5_client.BridgeClient`)
- [x] Idempotent on ticket / `external_id`; auto-create incomplete EA profiles by magic
- [x] Block 2 pattern grouping via `context_signature` → RAW_OBSERVATION /
      REPEATED_PATTERN (`KnowledgeEngineService.ingest_grouped_observation`)
- [x] Block 3 review queue: `list_knowledge_records_by_state` +
      `python -m phase3_knowledge_engine.review --state …` (read-only)
- [x] Block 4/5 EA version change: mandatory reason → `quarantine` +
      `ChangeLogEntry`; `confirm_ea_version_safe` (human only);
      `list_ea_profiles(status=…)`
- [x] Block 6 technical report: `build_technical_report` +
      `python -m phase3_knowledge_engine.report [--ea …]` (KNOWLEDGE only)
- No live streaming; no write-back to Phase 2
- Validate on staging with `PHASE3_KNOWLEDGE_ENGINE_ENABLED=true` (flag still default OFF)

## Gate 2 — Internal API (staging only)

- Mount `/api/knowledge/v1/*` on a **separate** FastAPI sub-app or process
- Still no dashboard tab
- Human reviewers use API or CLI to advance validation states

## Gate 3 — Dashboard Knowledge tab (opt-in)

- New React route `/knowledge` behind feature flag
- Read-only views: EA dossiers, validation queue, audit trail
- No mock knowledge mixed into Phase 2 supervision panel

## Gate 4 — Query engine

- Implement read models for:
  - Best session per EA
  - Loss conditions
  - Performance drift by version
  - Testing candidates
  - Supported conclusions
  - Restriction reasons

## Gate 5 — Decision support (human-gated)

- Suggestions only: “consider restricting EA X in session Y”
- Requires explicit human approval
- **Never** auto start/stop EAs or change capital

## Explicit non-goals (all gates)

- Automatic knowledge from single trades
- Silent knowledge rewrite
- Deletion of invalidated conclusions
- Integration with n8n closed-loop control before Gate 5 review

## Branch strategy

| Branch | Purpose |
|--------|---------|
| `cursor/fix-windows-clean-install-88da` | Phase 2 production fixes |
| `cursor/phase3-knowledge-engine-foundation` | This foundation |
| `main` | Restore after Phase 2 gate — Phase 3 merges later |

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

- Batch adapter: import closed trades from MT5 export or bridge JSON **into EvidenceItem**
- No live streaming; no write-back to Phase 2
- Run as standalone CLI: `python -m phase3_knowledge_engine.ingest --file trades.csv`
- Validate on staging with `PHASE3_KNOWLEDGE_ENGINE_ENABLED=true`

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

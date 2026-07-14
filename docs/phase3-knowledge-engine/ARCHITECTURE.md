# Phase 3 Architecture — Knowledge Management Engine

## Status

**Isolated foundation** — not integrated with Phase 2 production runtime.

## Objective

Transform trading results into traceable, validated knowledge that can eventually support decisions — without ever auto-promoting single trades to “knowledge”.

## Lifecycle

```
Data → Context → Hypothesis → Observation → Validation → Conclusion → Knowledge → Decision Support
```

Decision Support is **out of scope** for this foundation (Phase 4+).

## Layered architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 2 (UNTOUCHED)                                          │
│ Dashboard · server.py · MT5 Bridge · Installer · n8n        │
└─────────────────────────────────────────────────────────────┘
                          (no imports)
┌─────────────────────────────────────────────────────────────┐
│ phase3_knowledge_engine/                                     │
│                                                              │
│  domain/          Pure entities, rules, state machine        │
│  application/     KnowledgeEngineService use-cases           │
│  infrastructure/  SQLite knowledge.db repositories           │
│  api/contract.py  Future REST DTOs (not mounted)             │
└─────────────────────────────────────────────────────────────┘
```

## Validation state flow

```
RawObservation
        │
        ▼
RepeatedPattern
        │
        ▼
Hypothesis                    (explicit human act only)
        │
        ▼
EvidenceUnderReview
        │
        ├──► ProvisionallyValidatedConclusion
        │            │
        │            ▼
        │    FullyValidatedConclusion
        │            │
        │            ▼
        │    KnowledgeCandidate
        │            │
        │            ▼
        │       Knowledge
        │
        └──► InvalidatedConclusion  (preserved forever)
```

## Core invariants

1. One observation ≠ knowledge.
2. RepeatedPattern threshold is configurable (default 2) and never sufficient alone.
3. Hypothesis is always explicit.
4. Human review required for all validation milestones.
5. FullyValidated → KnowledgeCandidate → Knowledge (no shortcuts).
6. New evidence cannot silently rewrite knowledge.
7. Invalidated conclusions are never deleted.
8. Every transition produces an audit trail.
9. Confidence score is advisory only.

## Feature flag

```python
PHASE3_KNOWLEDGE_ENGINE_ENABLED = False  # config.py
```

Phase 2 code must not read this flag until integration gate.

## Persistence

| Store | File | Owner |
|-------|------|-------|
| Phase 2 operational data | `atlas.db` | Phase 2 backend |
| Phase 3 knowledge | `knowledge.db` | Phase 3 module |

## Future integration (see INTEGRATION_ROADMAP.md)

Read-only trade ingestion → staging API → dashboard Knowledge tab → decision support suggestions (human-gated).

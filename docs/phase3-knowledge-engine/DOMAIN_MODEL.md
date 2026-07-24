# Phase 3 Domain Model

## Entities

### EAKnowledgeProfile

Living dossier for an Expert Advisor (EA).

| Field | Description |
|-------|-------------|
| `ea_key` | Stable identifier (e.g. `london-scalper`) |
| `version` | Semver of the EA build |
| `purpose` | Strategic intent |
| `entry_rules` / `exit_rules` | Documented logic |
| `risk_rules` | JSON risk envelope |
| `permitted_symbols` | Allow-list |
| `permitted_sessions` | e.g. London, New York |
| `market_conditions` | Regime preferences |
| `status` | `active` \| `restricted` \| `stopped` \| `testing` |
| `known_strengths` / `known_weaknesses` | Curated lists |

Related collections (stored separately): test history, performance metrics, incidents, change log, knowledge records.

### EvidenceItem

Atomic fact linked to conclusions. Types: `trade`, `backtest_run`, `incident`, `metric_snapshot`.

Carries full trading context: symbol, session, regime, volatility, spread, PnL, drawdown, entry/exit reason, EA version, account type, test type.

### MarketContext

Contextual envelope: session, regime, volatility, spread, symbol, timestamp, weekday, notes.

### KnowledgeRecord

A statement progressing through validation states. Tracks evidence counts, sample size, date range, confidence (advisory), supporting/contradictory evidence IDs, review metadata, and promotion criteria fields.

### AuditTrailEntry

Immutable transition log: from/to state, actor, justification, evidence IDs, timestamp.

### EvidenceImpactRecord

Records how new evidence affected existing knowledge (`confirm`, `weaken`, `review`, `invalidate`) without silent rewrite.

## Relationships

```
EAKnowledgeProfile 1──* EvidenceItem
EAKnowledgeProfile 1──* KnowledgeRecord
KnowledgeRecord    1──* AuditTrailEntry
KnowledgeRecord    1──* EvidenceImpactRecord
EvidenceItem       *──1 MarketContext (optional)
```

## Validation states

See `VALIDATION_STATE_MODEL.md`.

## Domain principle

```python
KNOWLEDGE_PRINCIPLE = (
    "Knowledge is not what happened. Knowledge is what survived validation."
)
```

Defined in `phase3_knowledge_engine/domain/rules.py`.

Knowledge promotion numeric thresholds (`MIN_EVIDENCE_FOR_KNOWLEDGE`,
`MIN_SAMPLE_FOR_KNOWLEDGE`) are defined in `phase3_knowledge_engine/config.py`
and overrideable via `PHASE3_MIN_EVIDENCE_FOR_KNOWLEDGE` and
`PHASE3_MIN_SAMPLE_FOR_KNOWLEDGE` environment variables.

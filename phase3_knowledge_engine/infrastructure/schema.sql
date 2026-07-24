-- Atlas Phase 3 — Knowledge Management Engine
-- Separate database: knowledge.db (never atlas.db)
-- Schema version: 1

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS ea_profiles (
    id                  TEXT PRIMARY KEY,
    ea_key              TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    version             TEXT NOT NULL,
    purpose             TEXT NOT NULL,
    entry_rules         TEXT NOT NULL,
    exit_rules          TEXT NOT NULL,
    risk_rules_json     TEXT NOT NULL,
    permitted_symbols   TEXT NOT NULL,  -- JSON array
    permitted_sessions  TEXT NOT NULL,  -- JSON array
    market_conditions   TEXT NOT NULL,  -- JSON object
    status              TEXT NOT NULL DEFAULT 'testing',
    known_strengths     TEXT NOT NULL DEFAULT '[]',
    known_weaknesses    TEXT NOT NULL DEFAULT '[]',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_contexts (
    id              TEXT PRIMARY KEY,
    session         TEXT,
    market_regime   TEXT,
    volatility      REAL,
    spread          REAL,
    symbol          TEXT,
    occurred_at     TEXT,
    weekday         TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id                  TEXT PRIMARY KEY,
    ea_profile_id       TEXT NOT NULL REFERENCES ea_profiles(id),
    evidence_type       TEXT NOT NULL,
    occurred_at         TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    session             TEXT,
    market_regime       TEXT,
    volatility          REAL,
    spread              REAL,
    pnl                 REAL,
    drawdown            REAL,
    entry_reason        TEXT,
    exit_reason         TEXT,
    ea_version          TEXT,
    account_type        TEXT,
    test_type           TEXT,
    raw_payload_json    TEXT NOT NULL DEFAULT '{}',
    context_id          TEXT REFERENCES market_contexts(id),
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_ea ON evidence_items(ea_profile_id);
CREATE INDEX IF NOT EXISTS idx_evidence_occurred ON evidence_items(occurred_at);

CREATE TABLE IF NOT EXISTS knowledge_records (
    id                              TEXT PRIMARY KEY,
    ea_profile_id                   TEXT NOT NULL REFERENCES ea_profiles(id),
    validation_state                TEXT NOT NULL,
    statement                       TEXT NOT NULL,
    evidence_count                  INTEGER NOT NULL DEFAULT 0,
    sample_size                     INTEGER NOT NULL DEFAULT 0,
    date_range_start                TEXT,
    date_range_end                  TEXT,
    confidence_score                REAL NOT NULL DEFAULT 0.0,
    supporting_evidence_ids_json    TEXT NOT NULL DEFAULT '[]',
    contradictory_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
    last_reviewed_at                TEXT,
    reviewed_by                     TEXT,
    relevance_for_decisions         TEXT,
    context_documented              INTEGER NOT NULL DEFAULT 0,
    material_contradictions_resolved INTEGER NOT NULL DEFAULT 0,
    created_at                      TEXT NOT NULL,
    updated_at                      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_ea ON knowledge_records(ea_profile_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_state ON knowledge_records(validation_state);

CREATE TABLE IF NOT EXISTS audit_trail (
    id                  TEXT PRIMARY KEY,
    knowledge_record_id TEXT NOT NULL REFERENCES knowledge_records(id),
    from_state          TEXT NOT NULL,
    to_state            TEXT NOT NULL,
    transitioned_at     TEXT NOT NULL,
    actor               TEXT NOT NULL,
    justification       TEXT NOT NULL,
    evidence_ids_json   TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_trail(knowledge_record_id);

CREATE TABLE IF NOT EXISTS evidence_impacts (
    id                  TEXT PRIMARY KEY,
    knowledge_record_id TEXT NOT NULL REFERENCES knowledge_records(id),
    evidence_id         TEXT NOT NULL REFERENCES evidence_items(id),
    impact              TEXT NOT NULL,
    recorded_at         TEXT NOT NULL,
    actor               TEXT NOT NULL,
    notes               TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id              TEXT PRIMARY KEY,
    ea_profile_id   TEXT NOT NULL REFERENCES ea_profiles(id),
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    net_pnl         REAL NOT NULL,
    max_drawdown_pct REAL NOT NULL,
    win_rate        REAL,
    trade_count     INTEGER NOT NULL DEFAULT 0,
    sharpe          REAL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS change_log (
    id              TEXT PRIMARY KEY,
    ea_profile_id   TEXT NOT NULL REFERENCES ea_profiles(id),
    changed_at      TEXT NOT NULL,
    from_version    TEXT NOT NULL,
    to_version      TEXT NOT NULL,
    description     TEXT NOT NULL,
    effect_summary  TEXT
);

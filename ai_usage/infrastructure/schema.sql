-- Atlas AI usage — isolated token/cost ledger
-- Separate database: ai_usage.db (never atlas.db, never knowledge.db, never notifications.db)
-- Schema version: 1. Additive CREATE TABLE IF NOT EXISTS only.
-- Rows are append-only. There is no UPDATE or DELETE of usage records.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS ai_usage (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    mode                TEXT NOT NULL,
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER NOT NULL,
    estimated_cost_usd  TEXT NOT NULL,
    occurred_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_user_time
    ON ai_usage(user_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_ai_usage_occurred_at
    ON ai_usage(occurred_at);

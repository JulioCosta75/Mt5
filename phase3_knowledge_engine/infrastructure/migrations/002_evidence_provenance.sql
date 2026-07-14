-- Migration 002: evidence provenance for future MT5/backtest ingestion.
-- Idempotent: safe to run on databases that already have these columns.

ALTER TABLE evidence_items ADD COLUMN source_system TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE evidence_items ADD COLUMN external_id TEXT;
ALTER TABLE evidence_items ADD COLUMN ingestion_batch_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_source_external
    ON evidence_items(source_system, external_id)
    WHERE external_id IS NOT NULL;

UPDATE schema_meta SET value = '2' WHERE key = 'schema_version';

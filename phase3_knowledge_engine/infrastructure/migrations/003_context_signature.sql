-- Migration 003: context_signature for pre-hypothesis pattern grouping (Block 2).
-- Idempotent when applied via repository migration runner (column check).

ALTER TABLE knowledge_records ADD COLUMN context_signature TEXT;

CREATE INDEX IF NOT EXISTS idx_knowledge_context_signature
    ON knowledge_records(context_signature)
    WHERE context_signature IS NOT NULL;

UPDATE schema_meta SET value = '3' WHERE key = 'schema_version';

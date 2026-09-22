-- Additive column: which specific MT5 account produced this evidence.
-- NULL for older/manual rows. Idempotent when applied via repository runner.

ALTER TABLE evidence_items ADD COLUMN account_id TEXT;

CREATE INDEX IF NOT EXISTS idx_evidence_account
    ON evidence_items(account_id);

UPDATE schema_meta SET value = '4' WHERE key = 'schema_version';

-- Atlas notifications — isolated preference store
-- Separate database: notifications.db (never atlas.db, never knowledge.db)
-- Schema version: 1. Additive CREATE TABLE IF NOT EXISTS only.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS notification_preferences (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    account_id          TEXT NOT NULL,
    alert_type          TEXT NOT NULL,
    priority            TEXT NOT NULL,
    frequency           TEXT NOT NULL,
    channel             TEXT NOT NULL,
    quiet_hours_start   TEXT,
    quiet_hours_end     TEXT,
    active              INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pref_user_account_type_channel
    ON notification_preferences(user_id, account_id, alert_type, channel);

CREATE INDEX IF NOT EXISTS idx_pref_user_account
    ON notification_preferences(user_id, account_id);

CREATE TABLE IF NOT EXISTS notification_preference_audit (
    id              TEXT PRIMARY KEY,
    preference_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    field           TEXT NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    occurred_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pref_audit_preference
    ON notification_preference_audit(preference_id);

CREATE INDEX IF NOT EXISTS idx_pref_audit_user_account
    ON notification_preference_audit(user_id, account_id);

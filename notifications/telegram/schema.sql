-- Atlas notifications — isolated Telegram link tables (Stage 2a)
-- Same database file as Stage 1 preferences: notifications.db
-- Additive CREATE TABLE IF NOT EXISTS only. Never stores a phone number.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS telegram_link_codes (
    code         TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    account_id   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    consumed_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_telegram_link_codes_scope
    ON telegram_link_codes(user_id, account_id);

CREATE TABLE IF NOT EXISTS telegram_chat_links (
    chat_id      TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    account_id   TEXT NOT NULL,
    linked_at    TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_chat_user_account
    ON telegram_chat_links(user_id, account_id);

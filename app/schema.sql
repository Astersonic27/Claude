CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS kudos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id         INTEGER NOT NULL REFERENCES users(id),
    recipient_id      INTEGER NOT NULL REFERENCES users(id),
    message           TEXT    NOT NULL CHECK (length(message) BETWEEN 1 AND 500),
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    is_visible        INTEGER NOT NULL DEFAULT 1 CHECK (is_visible IN (0, 1)),
    moderated_by      INTEGER REFERENCES users(id),
    moderated_at      TEXT,
    moderation_reason TEXT,
    CHECK (sender_id <> recipient_id)
);
CREATE INDEX IF NOT EXISTS idx_kudos_feed   ON kudos (is_visible, id DESC);
CREATE INDEX IF NOT EXISTS idx_kudos_sender ON kudos (sender_id, created_at);

CREATE TABLE IF NOT EXISTS moderation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kudos_id   INTEGER NOT NULL,        -- no FK: row must outlive a deleted kudos
    admin_id   INTEGER NOT NULL REFERENCES users(id),
    action     TEXT    NOT NULL CHECK (action IN ('hide', 'unhide', 'delete')),
    reason     TEXT,
    message    TEXT,                    -- snapshot of the message for audit
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

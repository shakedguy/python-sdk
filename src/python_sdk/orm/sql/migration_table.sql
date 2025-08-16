CREATE TABLE IF NOT EXISTS schema_migrations
(
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    execution_ms INTEGER NOT NULL,
    dirty BOOLEAN NOT NULL DEFAULT FALSE
);
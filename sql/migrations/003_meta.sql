-- v3: generic key/value store.
-- Used to persist transient CLI state, e.g. the last search result ids so
-- `practice show` (no arg) can render them all.

CREATE TABLE meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
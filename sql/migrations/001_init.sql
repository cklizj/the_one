-- Deliberate Practice Tracker — schema v1
--
-- Canonical schema. db.py applies this via the schema_migrations table.
-- Conventions:
--   * All timestamps are ISO 8601 UTC strings.
--   * Subquestions are a JSON array of strings on the item row (v0 keeps
--     scheduling at item granularity; a normalized table can split later).
--   * Attempts are append-only; the latest row drives the next-review date.

CREATE TABLE items (
  id            INTEGER PRIMARY KEY,
  title         TEXT NOT NULL,
  domain        TEXT NOT NULL,
  subquestions  TEXT NOT NULL DEFAULT '[]',   -- JSON array of strings
  notes         TEXT NOT NULL DEFAULT '',
  code          TEXT NOT NULL DEFAULT '',
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);

CREATE TABLE tags (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE item_tags (
  item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (item_id, tag_id)
);

CREATE TABLE attempts (
  id          INTEGER PRIMARY KEY,
  item_id     INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  rated_at    TEXT NOT NULL,       -- UTC ISO timestamp
  rating      TEXT NOT NULL,       -- again | hard | good | easy
  next_review TEXT,                -- UTC ISO timestamp of next review
  reflection  TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_attempts_item ON attempts(item_id);
CREATE INDEX idx_attempts_next ON attempts(next_review);
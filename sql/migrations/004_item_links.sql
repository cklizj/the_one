-- v4: reference links (e.g. GitHub solution, docs, forum posts) per item.
--   links: JSON array of URL strings
-- Existing rows keep the empty-array default.

ALTER TABLE items ADD COLUMN links TEXT NOT NULL DEFAULT '[]';
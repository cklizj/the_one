-- v2: richer per-item content.
--   approach: free-form "brain flow" / how you reason through it (hidden at review)
--   related:  JSON array of related-concept names/links
--   media:    JSON array of file paths (images, diagrams, references)
-- Existing rows keep their (JSON) defaults, so this is safe to apply anywhere.

ALTER TABLE items ADD COLUMN approach TEXT NOT NULL DEFAULT '';
ALTER TABLE items ADD COLUMN related  TEXT NOT NULL DEFAULT '[]';
ALTER TABLE items ADD COLUMN media    TEXT NOT NULL DEFAULT '[]';
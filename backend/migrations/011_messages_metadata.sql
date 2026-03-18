-- 011 — Add metadata JSONB column to messages for storing structured agent output
-- (e.g. proposed_plan) so it can be reconstructed when loading history.

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS metadata JSONB;

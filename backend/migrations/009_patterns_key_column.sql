-- Add pattern_key column to patterns table (used by pattern_observer for time_avoidance
-- lookups and by user_notes service for user_preference entries).
ALTER TABLE patterns ADD COLUMN IF NOT EXISTS pattern_key TEXT;

-- Index for fast lookups by user + type + key
CREATE INDEX IF NOT EXISTS patterns_user_type_key_idx
    ON patterns (user_id, pattern_type, pattern_key);

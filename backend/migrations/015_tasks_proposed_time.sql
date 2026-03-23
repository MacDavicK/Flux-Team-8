-- Migration 015: Add proposed_time to tasks
--
-- proposed_time: intended wall-clock time for a recurring task, stored as
-- minutes since midnight in the user's local timezone (0–1439).
-- e.g. 9:00 AM = 540, 10:30 AM = 630.
--
-- Null for one-off tasks and tasks created before this migration.
--
-- Used by advance_recurring_task to preserve the original recurring time after
-- a single-occurrence reschedule — scheduled_at is the actual slot, proposed_time
-- is the canonical recurring time that the chain always returns to.

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS proposed_time INTEGER;

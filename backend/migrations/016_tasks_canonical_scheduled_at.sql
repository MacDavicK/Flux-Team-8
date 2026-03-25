-- Migration 016: Replace proposed_time with canonical_scheduled_at
--
-- canonical_scheduled_at: the UTC timestamp the RRULE would have generated for
-- this occurrence — i.e. the occurrence's position in the series independent of
-- any single-occurrence reschedule. Used as both the RRULE dtstart anchor and
-- the after_dt in advance_recurring_task, so:
--   - anchor drift is eliminated (series never inherits a rescheduled time)
--   - pull-back reschedules never produce a same-day duplicate occurrence
--
-- Set once at creation (= scheduled_at after all guards).
-- Updated only on series reschedule (both fields set to the same new value).
-- Never changed on single-occurrence reschedule (scheduled_at changes; this stays).
-- NULL for one-off (non-recurring) tasks.
-- NULL for rows created before this migration (recurrence.py falls back to scheduled_at).

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS canonical_scheduled_at TIMESTAMPTZ,
    DROP COLUMN IF EXISTS proposed_time;

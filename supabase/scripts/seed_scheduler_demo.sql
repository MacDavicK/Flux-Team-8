-- =============================================================
-- Flux Scheduler Agent Demo Seed Data
-- =============================================================
-- Run AFTER seed_test_data.sql (depends on Alice's user/goal/milestone rows).
-- Uses NOW() so timestamps are always relative to demo time.
--
-- Usage:
--   psql $DATABASE_URL -f supabase/scripts/seed_scheduler_demo.sql
--   OR paste into Supabase SQL Editor
-- =============================================================

-- ── 1. Update Alice's preferences with schedule data ────────
-- The SchedulerAgent reads preferences.sleep_window and preferences.work_hours
UPDATE users
SET preferences = jsonb_build_object(
  'theme', 'dark',
  'notifications', true,
  'sleep_window', jsonb_build_object('start', '23:00', 'end', '07:00'),
  'work_hours', jsonb_build_object(
    'start', '09:00',
    'end', '18:00',
    'days', jsonb_build_array('Mon','Tue','Wed','Thu','Fri')
  ),
  'chronotype', 'morning'
)
WHERE id = 'a1000000-0000-0000-0000-000000000001';

-- ── 2. Insert a DRIFTED task (the star of the demo) ─────────
-- Gym Session that was scheduled for this morning but drifted.
-- start_time = today 07:00 UTC, end_time = today 08:00 UTC
INSERT INTO tasks (id, user_id, goal_id, milestone_id, title, start_time, end_time, state, priority, trigger_type, is_recurring)
VALUES (
  'd2000000-0000-0000-0000-000000000001',
  'a1000000-0000-0000-0000-000000000001',
  'b1000000-0000-0000-0000-000000000001',
  'c1000000-0000-0000-0000-000000000002',
  'Gym Session',
  (CURRENT_DATE + INTERVAL '7 hours')::timestamptz,
  (CURRENT_DATE + INTERVAL '8 hours')::timestamptz,
  'drifted',
  'important',
  'time',
  true
)
ON CONFLICT (id) DO UPDATE SET
  start_time = EXCLUDED.start_time,
  end_time   = EXCLUDED.end_time,
  state      = 'drifted';

-- ── 3. Insert a couple SCHEDULED tasks for conflict detection ─
-- These exist so the agent's slot-finder has to work around them.

-- Lunch break today 12:00–12:45
INSERT INTO tasks (id, user_id, goal_id, milestone_id, title, start_time, end_time, state, priority, trigger_type, is_recurring)
VALUES (
  'd2000000-0000-0000-0000-000000000002',
  'a1000000-0000-0000-0000-000000000001',
  'b1000000-0000-0000-0000-000000000001',
  NULL,
  'Lunch Break',
  (CURRENT_DATE + INTERVAL '12 hours')::timestamptz,
  (CURRENT_DATE + INTERVAL '12 hours 45 minutes')::timestamptz,
  'scheduled',
  'standard',
  'time',
  true
)
ON CONFLICT (id) DO UPDATE SET
  start_time = EXCLUDED.start_time,
  end_time   = EXCLUDED.end_time,
  state      = 'scheduled';

-- Evening Spanish lesson today 19:00–19:30
INSERT INTO tasks (id, user_id, goal_id, milestone_id, title, start_time, end_time, state, priority, trigger_type, is_recurring)
VALUES (
  'd2000000-0000-0000-0000-000000000003',
  'a1000000-0000-0000-0000-000000000001',
  'b1000000-0000-0000-0000-000000000002',
  'c1000000-0000-0000-0000-000000000005',
  'Spanish Lesson',
  (CURRENT_DATE + INTERVAL '19 hours')::timestamptz,
  (CURRENT_DATE + INTERVAL '19 hours 30 minutes')::timestamptz,
  'scheduled',
  'standard',
  'time',
  true
)
ON CONFLICT (id) DO UPDATE SET
  start_time = EXCLUDED.start_time,
  end_time   = EXCLUDED.end_time,
  state      = 'scheduled';

-- ── 4. Verify ───────────────────────────────────────────────
-- Run this after insert to confirm:
SELECT id, title, state,
       to_char(start_time, 'HH24:MI') AS start_hh,
       to_char(end_time, 'HH24:MI')   AS end_hh
FROM tasks
WHERE user_id = 'a1000000-0000-0000-0000-000000000001'
ORDER BY start_time;

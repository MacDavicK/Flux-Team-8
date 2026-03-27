# Seed Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two idempotent demo seed scripts that populate `demo@flux.com` with 6 weeks of task history across 3 goals (Fitness, Health, Learning), today's tasks including aggressive-escalation urgent tasks, and proper data for all reflection-page analytics.

**Architecture:** `seed-local.sql` handles local Supabase by inserting directly into `auth.users` inside a `BEGIN/COMMIT` block with a `DO $$` block for variable-scoped inserts. `seed-hosted.sh` + `seed_hosted.py` handle hosted Supabase — bash loads `backend/.env`, Python uses supabase-py Admin SDK to manage the auth user and asyncpg for all data inserts in a single transaction. Both scripts delete-then-reseed on every run.

**Tech Stack:** PostgreSQL 15, asyncpg 0.29+, supabase-py 2.x Admin SDK, bash

---

## File Structure

| File | Purpose |
|------|---------|
| `backend/scripts/seed-local.sql` | Self-contained SQL — runs against local Supabase via Docker |
| `backend/scripts/seed_hosted.py` | Python — supabase-py Admin SDK + asyncpg bulk inserts |
| `backend/scripts/seed-hosted.sh` | Bash — loads `backend/.env`, checks deps, calls Python |

---

## Data Summary

**Streak guarantee:** Health daily check-ins cover days −6 through −1 (all `done`). Today has `done` tasks. Day −7 has only `missed` Health check-in and no other done tasks → streak breaks → exactly **7-day streak**.

**missed\_by\_category output:**
- Fitness: 4 missed (from 18 total historical tasks)
- Health: 8 missed (7 historical + today's vitamin)
- Learning: 3 missed (from 12 total historical tasks)

**Aggressive tasks:** Two pending tasks scheduled at `NOW() + 10 min` and `NOW() + 13 min` — notifier picks them up within one poll cycle.

---

### Task 1: Create `backend/scripts/seed-local.sql`

**Files:**
- Create: `backend/scripts/seed-local.sql`

- [ ] **Step 1: Create the scripts directory and write seed-local.sql**

```bash
mkdir -p backend/scripts
```

Then create `backend/scripts/seed-local.sql` with the following content:

```sql
-- ═══════════════════════════════════════════════════════════════
-- Flux Demo Seed — Local Supabase
-- Idempotent: re-running wipes demo@flux.com and re-seeds fresh.
--
-- Run:
--   docker run --rm --network=host postgres:15-alpine \
--     psql "postgresql://postgres:postgres@localhost:54322/postgres" \
--     -f backend/scripts/seed-local.sql
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- ─── 1. TRUNCATE ────────────────────────────────────────────────
DELETE FROM auth.users    WHERE email = 'demo@flux.com';
DELETE FROM public.users  WHERE email = 'demo@flux.com'; -- safety net

-- ─── 2. CREATE auth user ────────────────────────────────────────
-- migration 006_auth_user_trigger auto-creates public.users row.
INSERT INTO auth.users (
    id, instance_id,
    email, encrypted_password,
    email_confirmed_at,
    phone, phone_confirmed_at,
    raw_user_meta_data,
    role, aud,
    created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'demo@flux.com',
    crypt('demo@flux', gen_salt('bf')),
    NOW(),
    '+919820965355', NOW(),
    '{"name":"Krish"}'::jsonb,
    'authenticated', 'authenticated',
    NOW(), NOW()
);

DO $$
DECLARE
    v_uid  UUID;
    v_fit  UUID;
    v_hlth UUID;
    v_lrn  UUID;
BEGIN
    SELECT id INTO v_uid FROM auth.users WHERE email = 'demo@flux.com';

    -- ─── 3. UPDATE public.users with full profile ────────────────
    UPDATE public.users
    SET
        timezone              = 'Asia/Kolkata',
        onboarded             = true,
        phone_verified        = true,
        whatsapp_opt_in_at    = NOW(),
        push_subscription     = '{"endpoint":"https://stub.push.service/flux-demo","keys":{"p256dh":"BNcRdreALRFXTkOOUHK1EtK2wtZ","auth":"tBHItJI5svbpez7KI4CCXg"}}'::jsonb,
        profile               = jsonb_build_object(
            'name',          'Krish',
            'sleep_window',  jsonb_build_object('start','23:00','end','06:00'),
            'work_hours',    jsonb_build_object(
                                 'start','09:00','end','18:00',
                                 'days', to_jsonb(ARRAY['Mon','Tue','Wed','Thu','Fri'])),
            'chronotype',    'neutral',
            'existing_commitments', jsonb_build_array(
                jsonb_build_object(
                    'title','Gym',
                    'days', to_jsonb(ARRAY['Tuesday','Thursday']),
                    'time','19:00',
                    'duration_minutes', 60
                )
            )
        ),
        notification_preferences = jsonb_build_object(
            'phone_number',              '+919820965355',
            'whatsapp_opted_in',         true,
            'reminder_lead_minutes',     10,
            'escalation_window_minutes', 2
        ),
        updated_at = NOW()
    WHERE id = v_uid;

    -- ─── 4. INSERT goals (RETURNING id INTO var) ─────────────────
    INSERT INTO public.goals (
        user_id, title, description, class_tags, status,
        target_weeks, activated_at, plan_json
    ) VALUES (
        v_uid,
        'Run a 5K without stopping',
        'Build running endurance with a structured 6-week plan',
        ARRAY['Fitness'], 'active', 6,
        NOW() - INTERVAL '6 weeks',
        '{"goal_title":"Run a 5K without stopping","milestones":["Week 1: Run 1km non-stop","Week 3: Run 3km non-stop","Week 6: Complete 5K"],"weekly_task_count":3,"task_titles":["Morning run","Interval training","Long run"]}'::jsonb
    ) RETURNING id INTO v_fit;

    INSERT INTO public.goals (
        user_id, title, description, class_tags, status,
        target_weeks, activated_at, plan_json
    ) VALUES (
        v_uid,
        'Build a daily hydration habit',
        'Drink at least 2.5L of water every day for 4 weeks',
        ARRAY['Health'], 'active', 4,
        NOW() - INTERVAL '4 weeks',
        '{"goal_title":"Build a daily hydration habit","milestones":["Week 1: 7-day streak","Week 2: 14-day track","Week 4: Habit locked in"],"weekly_task_count":7,"task_titles":["Morning water intake","Mid-day hydration","Evening water check-in"]}'::jsonb
    ) RETURNING id INTO v_hlth;

    INSERT INTO public.goals (
        user_id, title, description, class_tags, status,
        target_weeks, activated_at, plan_json
    ) VALUES (
        v_uid,
        'Complete Python for Data Science course',
        'Finish all 8 modules and submit the capstone project',
        ARRAY['Learning'], 'active', 8,
        NOW() - INTERVAL '4 weeks',
        '{"goal_title":"Complete Python for Data Science course","milestones":["Week 2: NumPy & Pandas done","Week 5: ML basics done","Week 8: Capstone submitted"],"weekly_task_count":3,"task_titles":["Study session: lecture","Study session: exercises","Weekly project work"]}'::jsonb
    ) RETURNING id INTO v_lrn;

    -- ═══════════════════════════════════════════════════════════
    -- 5. HISTORICAL TASKS
    -- All times UTC. IST = UTC+5:30.
    -- Runs: 7 AM IST = 01:30 UTC | Check-ins: 8 AM IST = 02:30 UTC
    -- Study: 7:30 PM IST = 14:00 UTC
    -- ═══════════════════════════════════════════════════════════

    -- ── Fitness: weeks -6 to -5 (4 done, 2 missed) ─────────────
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '42 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'missed',
            (CURRENT_DATE - INTERVAL '40 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '38 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '35 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '33 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'missed',
            (CURRENT_DATE - INTERVAL '31 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard');

    -- ── Fitness: weeks -4 to -3 (5 done, 1 missed) ─────────────
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '28 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '26 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '24 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '21 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'missed',
            (CURRENT_DATE - INTERVAL '19 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '17 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard');

    -- ── Fitness: weeks -2 to -1 (5 done, 1 missed) ─────────────
    -- Day -7 is intentionally skipped to cap the streak at exactly 7 days.
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '14 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '12 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '10 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '8 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE - INTERVAL '5 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Morning run', 'missed',
            (CURRENT_DATE - INTERVAL '3 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard');

    -- ── Health: weeks -4 to -3 (10 done, 4 missed) ─────────────
    -- Days -28 to -15 (14 daily check-ins)
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '28 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '27 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '26 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '25 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '24 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '23 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '22 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '21 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '20 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '19 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '18 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '17 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '16 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '15 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent');

    -- ── Health: weeks -2 to -1 (11 done, 3 missed) ─────────────
    -- Days -14 to -1. Days -6 through -1 are ALL done (streak guarantee).
    -- Days -7, -8, -9 are missed (breaks streak after day -6).
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '14 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '13 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '12 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '11 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '10 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '9 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '8 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'missed',
            (CURRENT_DATE - INTERVAL '7 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '6 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '5 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '4 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '3 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '2 days'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'done',
            (CURRENT_DATE - INTERVAL '1 day'   + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent');

    -- ── Learning: weeks -4 to -3 (4 done, 2 missed) ─────────────
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_lrn, 'Study session: Pandas fundamentals', 'done',
            (CURRENT_DATE - INTERVAL '28 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: data wrangling exercises', 'done',
            (CURRENT_DATE - INTERVAL '26 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: visualization basics', 'missed',
            (CURRENT_DATE - INTERVAL '24 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: statistics with Python', 'done',
            (CURRENT_DATE - INTERVAL '21 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: probability concepts', 'missed',
            (CURRENT_DATE - INTERVAL '19 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: weekly project review', 'done',
            (CURRENT_DATE - INTERVAL '17 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard');

    -- ── Learning: weeks -2 to -1 (5 done, 1 missed) ─────────────
    -- Day -7 skipped (same as Fitness) to keep day -7 without done tasks.
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_lrn, 'Study session: NumPy arrays', 'done',
            (CURRENT_DATE - INTERVAL '14 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: linear algebra review', 'done',
            (CURRENT_DATE - INTERVAL '12 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: scikit-learn intro', 'done',
            (CURRENT_DATE - INTERVAL '10 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: regression models', 'done',
            (CURRENT_DATE - INTERVAL '8 days'  + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: classification basics', 'done',
            (CURRENT_DATE - INTERVAL '5 days'  + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: weekly project work', 'missed',
            (CURRENT_DATE - INTERVAL '3 days'  + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard');

    -- ── Standalone tasks (no goal — won't appear in missed_by_category) ──
    INSERT INTO public.tasks
        (user_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, 'Grocery run', 'missed',
            (CURRENT_DATE - INTERVAL '5 days' + INTERVAL '10 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, 'Doctor call', 'done',
            (CURRENT_DATE - INTERVAL '3 days' + INTERVAL '11 hours') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, 'Pay electricity bill', 'done',
            (CURRENT_DATE - INTERVAL '2 days' + INTERVAL '12 hours') AT TIME ZONE 'UTC', 15, 'standard');

    -- ═══════════════════════════════════════════════════════════
    -- 6. TODAY'S TASKS
    -- ═══════════════════════════════════════════════════════════
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        -- 7:00 AM IST (01:30 UTC) — done (contributes to today's streak day)
        (v_uid, v_fit, 'Morning run', 'done',
            (CURRENT_DATE + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        -- 8:00 AM IST (02:30 UTC) — done
        (v_uid, v_hlth, 'Drink 500ml water', 'done',
            (CURRENT_DATE + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        -- 9:00 AM IST (03:30 UTC) — missed (+1 to Health missed_by_category)
        (v_uid, v_hlth, 'Take vitamin supplements', 'missed',
            (CURRENT_DATE + INTERVAL '3 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'standard'),
        -- NOW + 10 min — AGGRESSIVE (notifier fires within 1 poll cycle)
        (v_uid, v_lrn, 'Study session: NumPy basics', 'pending',
            NOW() + INTERVAL '10 minutes', 60, 'aggressive'),
        -- NOW + 13 min — AGGRESSIVE
        (v_uid, v_fit, 'Evening run prep check-in', 'pending',
            NOW() + INTERVAL '13 minutes', 15, 'aggressive'),
        -- 1:00 PM IST (07:30 UTC) — pending
        (v_uid, v_hlth, 'Drink water before lunch', 'pending',
            (CURRENT_DATE + INTERVAL '7 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        -- 7:00 PM IST (13:30 UTC) — pending
        (v_uid, v_lrn, 'Evening study block', 'pending',
            (CURRENT_DATE + INTERVAL '13 hours 30 minutes') AT TIME ZONE 'UTC', 90, 'standard');

    -- ═══════════════════════════════════════════════════════════
    -- 7. FUTURE TASKS (next 2 weeks)
    -- ═══════════════════════════════════════════════════════════

    -- Fitness: 6 runs
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_fit, 'Morning run', 'pending',
            (CURRENT_DATE + INTERVAL '2 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Interval training', 'pending',
            (CURRENT_DATE + INTERVAL '4 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 40, 'standard'),
        (v_uid, v_fit, 'Long run', 'pending',
            (CURRENT_DATE + INTERVAL '7 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 45, 'standard'),
        (v_uid, v_fit, 'Morning run', 'pending',
            (CURRENT_DATE + INTERVAL '9 days'  + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 30, 'standard'),
        (v_uid, v_fit, 'Interval training', 'pending',
            (CURRENT_DATE + INTERVAL '11 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 40, 'standard'),
        (v_uid, v_fit, 'Long run — final 5K attempt', 'pending',
            (CURRENT_DATE + INTERVAL '14 days' + INTERVAL '1 hour 30 minutes') AT TIME ZONE 'UTC', 50, 'standard');

    -- Health: 7 daily check-ins
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '1 day'  + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '2 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '3 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '4 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '5 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '6 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent'),
        (v_uid, v_hlth, 'Daily water check-in', 'pending',
            (CURRENT_DATE + INTERVAL '7 days' + INTERVAL '2 hours 30 minutes') AT TIME ZONE 'UTC', 5, 'silent');

    -- Learning: 4 study sessions
    INSERT INTO public.tasks
        (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
    VALUES
        (v_uid, v_lrn, 'Study session: decision trees', 'pending',
            (CURRENT_DATE + INTERVAL '3 days'  + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: model evaluation', 'pending',
            (CURRENT_DATE + INTERVAL '6 days'  + INTERVAL '14 hours') AT TIME ZONE 'UTC', 60, 'standard'),
        (v_uid, v_lrn, 'Study session: capstone project start', 'pending',
            (CURRENT_DATE + INTERVAL '10 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 90, 'standard'),
        (v_uid, v_lrn, 'Study session: capstone project review', 'pending',
            (CURRENT_DATE + INTERVAL '13 days' + INTERVAL '14 hours') AT TIME ZONE 'UTC', 90, 'silent');

    -- ═══════════════════════════════════════════════════════════
    -- 8. PATTERNS
    -- ═══════════════════════════════════════════════════════════
    INSERT INTO public.patterns
        (user_id, pattern_type, pattern_key, description, data, confidence)
    VALUES
        (v_uid, 'category_performance', 'fitness_performance',
            'Fitness tasks: 78% completion rate over last 6 weeks',
            '{"category":"Fitness","completion_rate":0.78,"total_tasks":18,"done_tasks":14}'::jsonb,
            0.92),
        (v_uid, 'category_performance', 'health_performance',
            'Health tasks: 75% completion rate over last 4 weeks',
            '{"category":"Health","completion_rate":0.75,"total_tasks":28,"done_tasks":21}'::jsonb,
            0.88),
        (v_uid, 'category_performance', 'learning_performance',
            'Learning tasks: 75% completion rate over last 4 weeks',
            '{"category":"Learning","completion_rate":0.75,"total_tasks":12,"done_tasks":9}'::jsonb,
            0.85),
        (v_uid, 'time_avoidance', 'wednesday_afternoon',
            'Tends to miss tasks scheduled on Wednesday afternoons (14:00–16:00)',
            '{"window_start":"14:00","window_end":"16:00","day_of_week":"Wednesday","miss_rate":0.67,"sample_size":9}'::jsonb,
            0.82),
        (v_uid, 'completion_streak', 'current_streak',
            'Current streak: 7 days. Personal best: 12 days.',
            '{"current_streak":7,"peak_streak":12}'::jsonb,
            0.95);

END;
$$;

-- ─── 9. REFRESH materialized views ────────────────────────────
REFRESH MATERIALIZED VIEW user_weekly_stats;
REFRESH MATERIALIZED VIEW missed_by_category;
REFRESH MATERIALIZED VIEW activity_heatmap;

COMMIT;

SELECT 'Flux demo seed complete — demo@flux.com / demo@flux' AS status;
```

- [ ] **Step 2: Run against local Supabase**

Make sure local Supabase is running (`docker compose up`), then:

```bash
# From repo root:
PGPASSWORD=postgres docker run --rm --network=host postgres:15-alpine \
  psql "postgresql://postgres:postgres@localhost:54322/postgres" \
  -f backend/scripts/seed-local.sql
```

Expected output ends with:
```
status
-----------------------------------------------
Flux demo seed complete — demo@flux.com / demo@flux
(1 row)
```

- [ ] **Step 3: Verify the data**

```bash
PGPASSWORD=postgres docker run --rm --network=host postgres:15-alpine \
  psql "postgresql://postgres:postgres@localhost:54322/postgres" -c "
SELECT
  (SELECT COUNT(*) FROM public.goals    WHERE user_id=(SELECT id FROM public.users WHERE email='demo@flux.com')) AS goals,
  (SELECT COUNT(*) FROM public.tasks    WHERE user_id=(SELECT id FROM public.users WHERE email='demo@flux.com')) AS tasks,
  (SELECT COUNT(*) FROM public.patterns WHERE user_id=(SELECT id FROM public.users WHERE email='demo@flux.com')) AS patterns;
SELECT category, missed_count FROM missed_by_category
  WHERE user_id=(SELECT id FROM public.users WHERE email='demo@flux.com')
  ORDER BY missed_count DESC;
SELECT COUNT(DISTINCT DATE(scheduled_at)) AS streak_days
  FROM public.tasks
  WHERE user_id=(SELECT id FROM public.users WHERE email='demo@flux.com')
    AND status='done'
    AND scheduled_at >= CURRENT_DATE - INTERVAL '8 days';"
```

Expected:
- goals=3, tasks≈76, patterns=5
- missed_by_category: Health ~8, Fitness 4, Learning 3
- streak_days: 7 (today + last 6 days each have done tasks)

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed-local.sql
git commit -m "feat: add local Supabase demo seed script"
```

---

### Task 2: Create `backend/scripts/seed_hosted.py`

**Files:**
- Create: `backend/scripts/seed_hosted.py`

- [ ] **Step 1: Write seed_hosted.py**

Create `backend/scripts/seed_hosted.py`:

```python
#!/usr/bin/env python3
"""
Flux Demo Seed — Hosted Supabase
Idempotent: deletes demo@flux.com auth user and all their data, then re-seeds.

Called by seed-hosted.sh which sets these env vars:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import asyncpg

DEMO_EMAIL = "demo@flux.com"
DEMO_PASSWORD = "demo@flux"
DEMO_PHONE = "+919820965355"


def utc_ts(today: "datetime.date", days_offset: int, hour: int, minute: int = 0) -> datetime:
    """Return a UTC-aware datetime: today + days_offset at HH:MM UTC."""
    d = today + timedelta(days=days_offset)
    return datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=timezone.utc)


async def seed(supabase_url: str, service_role_key: str, database_url: str) -> None:
    # ── 1. Auth: delete existing user, create fresh ──────────────────
    try:
        from supabase import create_client
    except ImportError:
        sys.exit("ERROR: supabase package not installed. Run: pip install supabase>=2.0.0")

    sb = create_client(supabase_url, service_role_key)

    print("→ Checking for existing demo@flux.com auth user...")
    try:
        users_page = sb.auth.admin.list_users()
        for u in users_page:
            if getattr(u, "email", None) == DEMO_EMAIL:
                sb.auth.admin.delete_user(u.id)
                print(f"  Deleted auth user: {u.id}")
                break
    except Exception as exc:
        print(f"  Warning: could not list/delete auth users: {exc}")

    print("→ Creating demo@flux.com auth user...")
    result = sb.auth.admin.create_user(
        {
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "email_confirm": True,
            "phone": DEMO_PHONE,
            "phone_confirm": True,
            "user_metadata": {"name": "Krish"},
        }
    )
    uid = str(result.user.id)
    print(f"  Created: {uid}")

    # ── 2. asyncpg: all data in one transaction ───────────────────────
    # asyncpg requires postgresql:// not postgresql+asyncpg://
    pg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    print(f"→ Connecting to database...")
    conn = await asyncpg.connect(pg_url)

    try:
        async with conn.transaction():
            # Safety net: delete public.users row (cascade wasn't guaranteed)
            await conn.execute(
                "DELETE FROM public.users WHERE email = $1", DEMO_EMAIL
            )
            # Re-insert (trigger may not have fired for Admin SDK call)
            await conn.execute(
                "INSERT INTO public.users (id, email, created_at, updated_at) "
                "VALUES ($1, $2, NOW(), NOW()) ON CONFLICT (id) DO NOTHING",
                uid, DEMO_EMAIL,
            )

            # UPDATE profile
            await conn.execute(
                """
                UPDATE public.users SET
                    timezone              = 'Asia/Kolkata',
                    onboarded             = true,
                    phone_verified        = true,
                    whatsapp_opt_in_at    = NOW(),
                    push_subscription     = $1::jsonb,
                    profile               = $2::jsonb,
                    notification_preferences = $3::jsonb,
                    updated_at            = NOW()
                WHERE id = $4
                """,
                '{"endpoint":"https://stub.push.service/flux-demo","keys":{"p256dh":"BNcRdreALRFXTkOOUHK1EtK2wtZ","auth":"tBHItJI5svbpez7KI4CCXg"}}',
                '{"name":"Krish","sleep_window":{"start":"23:00","end":"06:00"},"work_hours":{"start":"09:00","end":"18:00","days":["Mon","Tue","Wed","Thu","Fri"]},"chronotype":"neutral","existing_commitments":[{"title":"Gym","days":["Tuesday","Thursday"],"time":"19:00","duration_minutes":60}]}',
                '{"phone_number":"+919820965355","whatsapp_opted_in":true,"reminder_lead_minutes":10,"escalation_window_minutes":2}',
                uid,
            )

            # INSERT goals
            fit = await conn.fetchval(
                """
                INSERT INTO public.goals
                    (user_id, title, description, class_tags, status, target_weeks, activated_at, plan_json)
                VALUES ($1,$2,$3,$4,'active',6,NOW()-INTERVAL '6 weeks',$5::jsonb)
                RETURNING id
                """,
                uid,
                "Run a 5K without stopping",
                "Build running endurance with a structured 6-week plan",
                ["Fitness"],
                '{"goal_title":"Run a 5K without stopping","milestones":["Week 1: Run 1km non-stop","Week 3: Run 3km non-stop","Week 6: Complete 5K"],"weekly_task_count":3,"task_titles":["Morning run","Interval training","Long run"]}',
            )

            hlth = await conn.fetchval(
                """
                INSERT INTO public.goals
                    (user_id, title, description, class_tags, status, target_weeks, activated_at, plan_json)
                VALUES ($1,$2,$3,$4,'active',4,NOW()-INTERVAL '4 weeks',$5::jsonb)
                RETURNING id
                """,
                uid,
                "Build a daily hydration habit",
                "Drink at least 2.5L of water every day for 4 weeks",
                ["Health"],
                '{"goal_title":"Build a daily hydration habit","milestones":["Week 1: 7-day streak","Week 2: 14-day track","Week 4: Habit locked in"],"weekly_task_count":7,"task_titles":["Morning water intake","Mid-day hydration","Evening water check-in"]}',
            )

            lrn = await conn.fetchval(
                """
                INSERT INTO public.goals
                    (user_id, title, description, class_tags, status, target_weeks, activated_at, plan_json)
                VALUES ($1,$2,$3,$4,'active',8,NOW()-INTERVAL '4 weeks',$5::jsonb)
                RETURNING id
                """,
                uid,
                "Complete Python for Data Science course",
                "Finish all 8 modules and submit the capstone project",
                ["Learning"],
                '{"goal_title":"Complete Python for Data Science course","milestones":["Week 2: NumPy & Pandas done","Week 5: ML basics done","Week 8: Capstone submitted"],"weekly_task_count":3,"task_titles":["Study session: lecture","Study session: exercises","Weekly project work"]}',
            )

            print(f"  Goals: fit={fit} hlth={hlth} lrn={lrn}")

            # INSERT tasks
            now = datetime.now(timezone.utc)
            today = now.date()

            def ts(days: int, hour: int, minute: int = 0) -> datetime:
                return utc_ts(today, days, hour, minute)

            # (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
            task_rows = [
                # Fitness: weeks -6 to -5 (4 done, 2 missed)
                (uid, fit, "Morning run", "done",   ts(-42, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-40, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-38, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-35, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-33, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-31, 1, 30), 30, "standard"),
                # Fitness: weeks -4 to -3 (5 done, 1 missed)
                (uid, fit, "Morning run", "done",   ts(-28, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-26, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-24, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-21, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-19, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-17, 1, 30), 30, "standard"),
                # Fitness: weeks -2 to -1 (5 done, 1 missed) — day -7 skipped for streak
                (uid, fit, "Morning run", "done",   ts(-14, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-12, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts(-10, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts( -8, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done",   ts( -5, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts( -3, 1, 30), 30, "standard"),
                # Health: weeks -4 to -3 (10 done, 4 missed) — days -28 to -15
                (uid, hlth, "Daily water check-in", "done",   ts(-28, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-27, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-26, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-25, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-24, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-23, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-22, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-21, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-20, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-19, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts(-18, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts(-17, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts(-16, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts(-15, 2, 30), 5, "silent"),
                # Health: weeks -2 to -1 (11 done, 3 missed) — days -14 to -1
                # Days -6 through -1 are ALL done for the 7-day streak guarantee.
                (uid, hlth, "Daily water check-in", "done",   ts(-14, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-13, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-12, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-11, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts(-10, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts( -9, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts( -8, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "missed", ts( -7, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -6, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -5, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -4, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -3, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -2, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done",   ts( -1, 2, 30), 5, "silent"),
                # Learning: weeks -4 to -3 (4 done, 2 missed)
                (uid, lrn, "Study session: Pandas fundamentals",    "done",   ts(-28, 14), 60, "standard"),
                (uid, lrn, "Study session: data wrangling exercises","done",   ts(-26, 14), 60, "standard"),
                (uid, lrn, "Study session: visualization basics",    "missed", ts(-24, 14), 60, "standard"),
                (uid, lrn, "Study session: statistics with Python",  "done",   ts(-21, 14), 60, "standard"),
                (uid, lrn, "Study session: probability concepts",    "missed", ts(-19, 14), 60, "standard"),
                (uid, lrn, "Study session: weekly project review",   "done",   ts(-17, 14), 60, "standard"),
                # Learning: weeks -2 to -1 (5 done, 1 missed) — day -7 skipped
                (uid, lrn, "Study session: NumPy arrays",         "done",   ts(-14, 14), 60, "standard"),
                (uid, lrn, "Study session: linear algebra review","done",   ts(-12, 14), 60, "standard"),
                (uid, lrn, "Study session: scikit-learn intro",   "done",   ts(-10, 14), 60, "standard"),
                (uid, lrn, "Study session: regression models",    "done",   ts( -8, 14), 60, "standard"),
                (uid, lrn, "Study session: classification basics","done",   ts( -5, 14), 60, "standard"),
                (uid, lrn, "Study session: weekly project work",  "missed", ts( -3, 14), 60, "standard"),
                # Standalone (no goal)
                (uid, None, "Grocery run",          "missed", ts(-5, 10), 60, "standard"),
                (uid, None, "Doctor call",           "done",   ts(-3, 11), 30, "standard"),
                (uid, None, "Pay electricity bill",  "done",   ts(-2, 12), 15, "standard"),
                # Today's tasks
                (uid, fit,  "Morning run",              "done",   ts(0, 1, 30), 30, "standard"),
                (uid, hlth, "Drink 500ml water",        "done",   ts(0, 2, 30), 5,  "silent"),
                (uid, hlth, "Take vitamin supplements", "missed", ts(0, 3, 30), 5,  "standard"),
                (uid, lrn,  "Study session: NumPy basics",      "pending",
                    now + timedelta(minutes=10), 60, "aggressive"),
                (uid, fit,  "Evening run prep check-in",        "pending",
                    now + timedelta(minutes=13), 15, "aggressive"),
                (uid, hlth, "Drink water before lunch", "pending", ts(0, 7, 30), 5,  "silent"),
                (uid, lrn,  "Evening study block",      "pending", ts(0, 13, 30), 90, "standard"),
                # Future tasks — Fitness
                (uid, fit, "Morning run",                  "pending", ts( 2, 1, 30), 30, "standard"),
                (uid, fit, "Interval training",            "pending", ts( 4, 1, 30), 40, "standard"),
                (uid, fit, "Long run",                     "pending", ts( 7, 1, 30), 45, "standard"),
                (uid, fit, "Morning run",                  "pending", ts( 9, 1, 30), 30, "standard"),
                (uid, fit, "Interval training",            "pending", ts(11, 1, 30), 40, "standard"),
                (uid, fit, "Long run — final 5K attempt",  "pending", ts(14, 1, 30), 50, "standard"),
                # Future tasks — Health
                (uid, hlth, "Daily water check-in", "pending", ts(1, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(2, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(3, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(4, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(5, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(6, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "pending", ts(7, 2, 30), 5, "silent"),
                # Future tasks — Learning
                (uid, lrn, "Study session: decision trees",          "pending", ts( 3, 14), 60, "standard"),
                (uid, lrn, "Study session: model evaluation",        "pending", ts( 6, 14), 60, "standard"),
                (uid, lrn, "Study session: capstone project start",  "pending", ts(10, 14), 90, "standard"),
                (uid, lrn, "Study session: capstone project review", "pending", ts(13, 14), 90, "silent"),
            ]

            await conn.executemany(
                """
                INSERT INTO public.tasks
                    (user_id, goal_id, title, status, scheduled_at, duration_minutes, escalation_policy)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                task_rows,
            )
            print(f"  Inserted {len(task_rows)} tasks")

            # INSERT patterns
            pattern_rows = [
                (uid, "category_performance", "fitness_performance",
                 "Fitness tasks: 78% completion rate over last 6 weeks",
                 '{"category":"Fitness","completion_rate":0.78,"total_tasks":18,"done_tasks":14}',
                 0.92),
                (uid, "category_performance", "health_performance",
                 "Health tasks: 75% completion rate over last 4 weeks",
                 '{"category":"Health","completion_rate":0.75,"total_tasks":28,"done_tasks":21}',
                 0.88),
                (uid, "category_performance", "learning_performance",
                 "Learning tasks: 75% completion rate over last 4 weeks",
                 '{"category":"Learning","completion_rate":0.75,"total_tasks":12,"done_tasks":9}',
                 0.85),
                (uid, "time_avoidance", "wednesday_afternoon",
                 "Tends to miss tasks scheduled on Wednesday afternoons (14:00–16:00)",
                 '{"window_start":"14:00","window_end":"16:00","day_of_week":"Wednesday","miss_rate":0.67,"sample_size":9}',
                 0.82),
                (uid, "completion_streak", "current_streak",
                 "Current streak: 7 days. Personal best: 12 days.",
                 '{"current_streak":7,"peak_streak":12}',
                 0.95),
            ]

            await conn.executemany(
                """
                INSERT INTO public.patterns
                    (user_id, pattern_type, pattern_key, description, data, confidence)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                pattern_rows,
            )
            print(f"  Inserted {len(pattern_rows)} patterns")

        # ── 3. REFRESH materialized views (outside transaction) ───────
        print("→ Refreshing materialized views...")
        for view in ("user_weekly_stats", "missed_by_category", "activity_heatmap"):
            await conn.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
            print(f"  Refreshed {view}")

    finally:
        await conn.close()

    print("\n✓ Flux demo seed complete — demo@flux.com / demo@flux")


if __name__ == "__main__":
    required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        sys.exit(f"ERROR: missing env vars: {', '.join(missing)}")

    asyncio.run(
        seed(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            os.environ["DATABASE_URL"],
        )
    )
```

- [ ] **Step 2: Verify the file is syntactically valid**

```bash
python3 -m py_compile backend/scripts/seed_hosted.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_hosted.py
git commit -m "feat: add hosted Supabase demo seed script (Python)"
```

---

### Task 3: Create `backend/scripts/seed-hosted.sh`

**Files:**
- Create: `backend/scripts/seed-hosted.sh`

- [ ] **Step 1: Write seed-hosted.sh**

Create `backend/scripts/seed-hosted.sh`:

```bash
#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Flux Demo Seed — Hosted Supabase
# Usage: bash backend/scripts/seed-hosted.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/backend/.env"

# ─── Load env ──────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: backend/.env not found. Copy backend/.env.example and fill it in."
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ─── Validate required vars ────────────────────────────────────
missing=()
for var in SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY DATABASE_URL; do
    [[ -z "${!var:-}" ]] && missing+=("$var")
done

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: missing required env vars in backend/.env:"
    printf '  - %s\n' "${missing[@]}"
    exit 1
fi

echo "→ Supabase URL: $SUPABASE_URL"
echo "→ Database URL: ${DATABASE_URL//:*@/:***@}"

# ─── Check Python deps ─────────────────────────────────────────
echo "→ Checking Python dependencies..."
python3 -c "import supabase" 2>/dev/null || {
    echo "ERROR: supabase package not installed."
    echo "  Run: pip install 'supabase>=2.0.0'"
    exit 1
}
python3 -c "import asyncpg" 2>/dev/null || {
    echo "ERROR: asyncpg package not installed."
    echo "  Run: pip install 'asyncpg>=0.29.0'"
    exit 1
}

# ─── Run seed ──────────────────────────────────────────────────
echo "→ Running seed script..."
python3 "${SCRIPT_DIR}/seed_hosted.py"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x backend/scripts/seed-hosted.sh
```

- [ ] **Step 3: Dry-run check (validates env loading, no DB required)**

```bash
# Check the script parses without error (no DB call without real env)
bash -n backend/scripts/seed-hosted.sh && echo "syntax OK"
```

Expected: `syntax OK`

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed-hosted.sh
git commit -m "feat: add hosted Supabase demo seed entrypoint (bash)"
```

---

### Task 4: End-to-End Smoke Test

**No files changed — verification only.**

- [ ] **Step 1: Run against local Supabase**

Ensure local Supabase is running:
```bash
docker compose up -d
```

Run the seed:
```bash
PGPASSWORD=postgres docker run --rm --network=host postgres:15-alpine \
  psql "postgresql://postgres:postgres@localhost:54322/postgres" \
  -f backend/scripts/seed-local.sql
```

- [ ] **Step 2: Log in and check the reflection page**

1. Open the app at `http://localhost:3000`
2. Log in with `demo@flux.com` / `demo@flux`
3. Navigate to `/reflection`

Expected on reflection page:
- **Streak:** 7
- **Focus Distribution:** 3 bars — Health (largest ~53%), Fitness (~27%), Learning (~20%)
- **Goal Progress Card:** 3 goals, all active with partial completion rings
- **Today's tasks:** 2 done (morning run + water), 1 missed (vitamins), 4 pending (2 labeled urgent)

- [ ] **Step 3: Re-run to verify idempotence**

```bash
PGPASSWORD=postgres docker run --rm --network=host postgres:15-alpine \
  psql "postgresql://postgres:postgres@localhost:54322/postgres" \
  -f backend/scripts/seed-local.sql
```

Expected: same output, no duplicate-key errors, page still shows identical data.

- [ ] **Step 4: Run against hosted (if available)**

```bash
bash backend/scripts/seed-hosted.sh
```

Expected final line: `✓ Flux demo seed complete — demo@flux.com / demo@flux`

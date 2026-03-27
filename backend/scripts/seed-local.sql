-- ═══════════════════════════════════════════════════════════════
-- Flux Demo Seed — Local Supabase
-- Idempotent: re-running wipes ALL data and re-seeds fresh.
--
-- Run:
--   docker run --rm --network=host postgres:15-alpine \
--     psql "postgresql://postgres:postgres@localhost:54322/postgres" \
--     -f backend/scripts/seed-local.sql
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- ─── 1. TRUNCATE (wipe all data) ────────────────────────────────
TRUNCATE public.dispatch_log, public.notification_log, public.messages,
         public.patterns, public.tasks, public.conversations,
         public.goals, public.users;
DELETE FROM auth.users;

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
        push_subscription     = NULL,
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
            'call_opted_in',             true,
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
            NOW() + INTERVAL '12 minutes', 60, 'aggressive'),
        -- NOW + 13 min — AGGRESSIVE
        (v_uid, v_fit, 'Evening run prep check-in', 'pending',
            NOW() + INTERVAL '15 minutes', 15, 'aggressive'),
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

    -- ── Set trigger_type on all time-based tasks (column has no default) ──
    UPDATE public.tasks SET trigger_type = 'time' WHERE user_id = v_uid AND trigger_type IS NULL;

END;
$$;

-- ─── 9. REFRESH materialized views ────────────────────────────
REFRESH MATERIALIZED VIEW user_weekly_stats;
REFRESH MATERIALIZED VIEW missed_by_category;
REFRESH MATERIALIZED VIEW activity_heatmap;

COMMIT;

SELECT 'Flux demo seed complete — demo@flux.com / demo@flux' AS status;

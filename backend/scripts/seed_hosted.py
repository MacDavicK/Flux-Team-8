#!/usr/bin/env python3
"""
Flux Demo Seed — Hosted Supabase
Idempotent: wipes ALL data and auth users, then re-seeds.

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


def utc_ts(
    today: "datetime.date", days_offset: int, hour: int, minute: int = 0
) -> datetime:
    """Return a UTC-aware datetime: today + days_offset at HH:MM UTC."""
    d = today + timedelta(days=days_offset)
    return datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=timezone.utc)


async def seed(supabase_url: str, service_role_key: str, database_url: str) -> None:
    # ── 1. Auth: delete existing user, create fresh ──────────────────
    try:
        from supabase import create_client
    except ImportError:
        sys.exit(
            "ERROR: supabase package not installed. Run: pip install supabase>=2.0.0"
        )

    sb = create_client(supabase_url, service_role_key)

    # ── 2. asyncpg: connect and wipe everything first ─────────────────
    # asyncpg requires postgresql:// not postgresql+asyncpg://
    pg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    print("→ Connecting to database...")
    conn = await asyncpg.connect(pg_url)

    try:
        # Wipe public tables + auth users directly via SQL (more reliable than Admin SDK)
        print("→ Truncating all tables...")
        await conn.execute(
            "TRUNCATE public.dispatch_log, public.notification_log, public.messages,"
            " public.patterns, public.tasks, public.conversations,"
            " public.goals, public.users"
        )
        await conn.execute("DELETE FROM auth.users")
        print("  Done.")

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

        async with conn.transaction():
            # Re-insert (trigger may not have fired for Admin SDK call)
            await conn.execute(
                "INSERT INTO public.users (id, email, created_at, updated_at) "
                "VALUES ($1, $2, NOW(), NOW()) ON CONFLICT (id) DO NOTHING",
                uid,
                DEMO_EMAIL,
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
                '{"phone_number":"+919820965355","whatsapp_opted_in":true,"call_opted_in":true,"reminder_lead_minutes":10,"escalation_window_minutes":2}',
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
                (uid, fit, "Morning run", "done", ts(-42, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-40, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-38, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-35, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-33, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-31, 1, 30), 30, "standard"),
                # Fitness: weeks -4 to -3 (5 done, 1 missed)
                (uid, fit, "Morning run", "done", ts(-28, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-26, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-24, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-21, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-19, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-17, 1, 30), 30, "standard"),
                # Fitness: weeks -2 to -1 (5 done, 1 missed) — day -7 skipped for streak
                (uid, fit, "Morning run", "done", ts(-14, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-12, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-10, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-8, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "done", ts(-5, 1, 30), 30, "standard"),
                (uid, fit, "Morning run", "missed", ts(-3, 1, 30), 30, "standard"),
                # Health: weeks -4 to -3 (10 done, 4 missed) — days -28 to -15
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-28, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-27, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-26, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-25, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-24, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-23, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-22, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-21, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-20, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-19, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-18, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-17, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-16, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-15, 2, 30),
                    5,
                    "silent",
                ),
                # Health: weeks -2 to -1 (11 done, 3 missed) — days -14 to -1
                # Days -6 through -1 are ALL done for the 7-day streak guarantee.
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-14, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-13, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-12, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-11, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "done",
                    ts(-10, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-9, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-8, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "missed",
                    ts(-7, 2, 30),
                    5,
                    "silent",
                ),
                (uid, hlth, "Daily water check-in", "done", ts(-6, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done", ts(-5, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done", ts(-4, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done", ts(-3, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done", ts(-2, 2, 30), 5, "silent"),
                (uid, hlth, "Daily water check-in", "done", ts(-1, 2, 30), 5, "silent"),
                # Learning: weeks -4 to -3 (4 done, 2 missed)
                (
                    uid,
                    lrn,
                    "Study session: Pandas fundamentals",
                    "done",
                    ts(-28, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: data wrangling exercises",
                    "done",
                    ts(-26, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: visualization basics",
                    "missed",
                    ts(-24, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: statistics with Python",
                    "done",
                    ts(-21, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: probability concepts",
                    "missed",
                    ts(-19, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: weekly project review",
                    "done",
                    ts(-17, 14),
                    60,
                    "standard",
                ),
                # Learning: weeks -2 to -1 (5 done, 1 missed) — day -7 skipped
                (
                    uid,
                    lrn,
                    "Study session: NumPy arrays",
                    "done",
                    ts(-14, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: linear algebra review",
                    "done",
                    ts(-12, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: scikit-learn intro",
                    "done",
                    ts(-10, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: regression models",
                    "done",
                    ts(-8, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: classification basics",
                    "done",
                    ts(-5, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: weekly project work",
                    "missed",
                    ts(-3, 14),
                    60,
                    "standard",
                ),
                # Standalone (no goal)
                (uid, None, "Grocery run", "missed", ts(-5, 10), 60, "standard"),
                (uid, None, "Doctor call", "done", ts(-3, 11), 30, "standard"),
                (uid, None, "Pay electricity bill", "done", ts(-2, 12), 15, "standard"),
                # Today's tasks
                (uid, fit, "Morning run", "done", ts(0, 1, 30), 30, "standard"),
                (uid, hlth, "Drink 500ml water", "done", ts(0, 2, 30), 5, "silent"),
                (
                    uid,
                    hlth,
                    "Take vitamin supplements",
                    "missed",
                    ts(0, 3, 30),
                    5,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: NumPy basics",
                    "pending",
                    now + timedelta(minutes=10),
                    60,
                    "aggressive",
                ),
                (
                    uid,
                    fit,
                    "Evening run prep check-in",
                    "pending",
                    now + timedelta(minutes=13),
                    15,
                    "aggressive",
                ),
                (
                    uid,
                    hlth,
                    "Drink water before lunch",
                    "pending",
                    ts(0, 7, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    lrn,
                    "Evening study block",
                    "pending",
                    ts(0, 13, 30),
                    90,
                    "standard",
                ),
                # Future tasks — Fitness
                (uid, fit, "Morning run", "pending", ts(2, 1, 30), 30, "standard"),
                (
                    uid,
                    fit,
                    "Interval training",
                    "pending",
                    ts(4, 1, 30),
                    40,
                    "standard",
                ),
                (uid, fit, "Long run", "pending", ts(7, 1, 30), 45, "standard"),
                (uid, fit, "Morning run", "pending", ts(9, 1, 30), 30, "standard"),
                (
                    uid,
                    fit,
                    "Interval training",
                    "pending",
                    ts(11, 1, 30),
                    40,
                    "standard",
                ),
                (
                    uid,
                    fit,
                    "Long run — final 5K attempt",
                    "pending",
                    ts(14, 1, 30),
                    50,
                    "standard",
                ),
                # Future tasks — Health
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(1, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(2, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(3, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(4, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(5, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(6, 2, 30),
                    5,
                    "silent",
                ),
                (
                    uid,
                    hlth,
                    "Daily water check-in",
                    "pending",
                    ts(7, 2, 30),
                    5,
                    "silent",
                ),
                # Future tasks — Learning
                (
                    uid,
                    lrn,
                    "Study session: decision trees",
                    "pending",
                    ts(3, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: model evaluation",
                    "pending",
                    ts(6, 14),
                    60,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: capstone project start",
                    "pending",
                    ts(10, 14),
                    90,
                    "standard",
                ),
                (
                    uid,
                    lrn,
                    "Study session: capstone project review",
                    "pending",
                    ts(13, 14),
                    90,
                    "silent",
                ),
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
                (
                    uid,
                    "category_performance",
                    "fitness_performance",
                    "Fitness tasks: 78% completion rate over last 6 weeks",
                    '{"category":"Fitness","completion_rate":0.78,"total_tasks":18,"done_tasks":14}',
                    0.92,
                ),
                (
                    uid,
                    "category_performance",
                    "health_performance",
                    "Health tasks: 75% completion rate over last 4 weeks",
                    '{"category":"Health","completion_rate":0.75,"total_tasks":28,"done_tasks":21}',
                    0.88,
                ),
                (
                    uid,
                    "category_performance",
                    "learning_performance",
                    "Learning tasks: 75% completion rate over last 4 weeks",
                    '{"category":"Learning","completion_rate":0.75,"total_tasks":12,"done_tasks":9}',
                    0.85,
                ),
                (
                    uid,
                    "time_avoidance",
                    "wednesday_afternoon",
                    "Tends to miss tasks scheduled on Wednesday afternoons (14:00–16:00)",
                    '{"window_start":"14:00","window_end":"16:00","day_of_week":"Wednesday","miss_rate":0.67,"sample_size":9}',
                    0.82,
                ),
                (
                    uid,
                    "completion_streak",
                    "current_streak",
                    "Current streak: 7 days. Personal best: 12 days.",
                    '{"current_streak":7,"peak_streak":12}',
                    0.95,
                ),
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

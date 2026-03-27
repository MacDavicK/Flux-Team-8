# Seed Script Design — Demo Data for Flux

**Date:** 2026-03-28
**Status:** Approved
**Author:** Claude (brainstorming session)

---

## Overview

Two idempotent seed scripts that populate a `demo@flux.com` user with realistic, demo-worthy data covering 3 goals (Fitness, Health, Learning), 6+ weeks of task history, and proper reflection-page analytics. Re-running either script wipes only the demo user's data and re-seeds fresh.

---

## 1. Script Architecture

```
backend/scripts/
├── seed-local.sql       # Raw SQL — for local Supabase dev instance
├── seed-hosted.sh       # Bash wrapper — reads backend/.env, calls Python
└── seed_hosted.py       # Python — Supabase Admin SDK + asyncpg bulk insert
```

### seed-local.sql
- Self-contained SQL file
- Deletes `auth.users` row by email → cascade-wipes all `public.*` data
- Inserts directly into `auth.users` (accessible on local Supabase)
- `006_auth_user_trigger` auto-creates the `public.users` row; script then UPDATEs it with profile/prefs
- All timestamps use `NOW()` expressions (relative to run time)
- Ends with `REFRESH MATERIALIZED VIEW` for all 3 analytics views
- Run with Docker (same pattern as `setup.sh`):
  ```bash
  docker run --rm --network=host postgres:15-alpine \
    psql "postgresql://postgres:postgres@localhost:54322/postgres" \
    -f backend/scripts/seed-local.sql
  ```

### seed-hosted.sh
- Reads `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` from `backend/.env`
- Rewrites `postgresql+asyncpg://` → `postgresql://` for display, passes raw URL to Python
- Checks for required Python deps (`supabase`, `asyncpg`), exits with clear error if missing
- Calls `seed_hosted.py`

### seed_hosted.py
- Loads env vars passed by bash script
- Uses `supabase-py` (service role) to:
  1. Find existing `demo@flux.com` auth user → `delete_user(uid)` if found
  2. `DELETE FROM public.users WHERE email = 'demo@flux.com'` (safety net, cascade)
  3. `create_user({ email, password, email_confirm: true, phone, phone_confirm: true })`
- Opens one `asyncpg` connection to `DATABASE_URL`
- Runs a single transaction: UPDATE users profile/prefs + INSERT goals + INSERT tasks + INSERT patterns
- Ends with `REFRESH MATERIALIZED VIEW CONCURRENTLY` for all 3 views
- Prints a summary on success

---

## 2. Demo User

| Field | Value |
|---|---|
| Email | `demo@flux.com` |
| Password | `demo@flux` |
| Name | Krish |
| Timezone | `Asia/Kolkata` (UTC+5:30) |
| Phone | `+919820965355` |
| `phone_verified` | `true` |
| `whatsapp_opt_in_at` | seed run timestamp |
| Onboarded | `true` |
| Chronotype | `neutral` |
| Sleep window | `23:00` → `06:00` |
| Work window | Mon–Fri, `09:00` → `18:00` |
| Existing commitments | Gym — Tue & Thu @ 19:00, 60 min |
| `reminder_lead_minutes` | `10` |
| `escalation_window_minutes` | `2` |
| Push subscription | stub object (non-functional, for demo) |

---

## 3. Goals

Three active goals, all with `activated_at` set to a past date and realistic `plan_json` snapshots.

| # | Title | `class_tags` | `target_weeks` | `activated_at` | Expected completion % |
|---|---|---|---|---|---|
| 1 | "Run a 5K without stopping" | `['Fitness']` | 6 | 6 weeks ago | ~72% |
| 2 | "Build a daily hydration habit" | `['Health']` | 4 | 4 weeks ago | ~85% |
| 3 | "Complete Python for Data Science course" | `['Learning']` | 8 | 4 weeks ago | ~58% |

`plan_json` for each goal contains a lightweight snapshot with `goal_title`, `milestones`, `weekly_task_count`, and `task_titles` — enough to look real in any debug views.

---

## 4. Task Timeline

All `scheduled_at` values are UTC. IST = UTC+5:30. "NOW()" means the moment the script runs.

### 4a. Historical tasks (for streak + weekly stats + missed_by_category)

Goal 1 — Fitness (Running, 3×/week):
- Weeks -6 to -5: 6 tasks — 4 `done`, 2 `missed`
- Weeks -4 to -3: 6 tasks — 5 `done`, 1 `missed`
- Weeks -2 to -1: 6 tasks — 5 `done`, 1 `missed`

Goal 2 — Health (Daily hydration check-in):
- Weeks -4 to -3: 14 tasks — 10 `done`, 4 `missed`
- Weeks -2 to -1: 14 tasks — 11 `done`, 3 `missed`

Goal 3 — Learning (Study sessions, 3×/week):
- Weeks -4 to -3: 6 tasks — 4 `done`, 2 `missed`
- Weeks -2 to -1: 6 tasks — 5 `done`, 1 `missed`

Standalone past tasks (no goal):
- "Grocery run" — 5 days ago — `missed`
- "Doctor call" — 3 days ago — `done`
- "Pay electricity bill" — 2 days ago — `done`

This produces:
- **7-day streak** (tasks done today + 6 prior days)
- `missed_by_category`: Fitness ~4 missed, Health ~7 missed, Learning ~3 missed
- 6 weeks of `user_weekly_stats` data

### 4b. Today's tasks

| Title | Goal | `scheduled_at` (IST) | Status | `escalation_policy` |
|---|---|---|---|---|
| Morning run | Fitness | 7:00 AM (past) | `done` | `standard` |
| Drink 500ml water | Health | 8:00 AM (past) | `done` | `silent` |
| Take vitamin supplements | Health | 9:00 AM (past) | `missed` | `standard` |
| Study session: NumPy basics | Learning | NOW + 10 min | `pending` | **`aggressive`** |
| Evening run prep check-in | Fitness | NOW + 13 min | `pending` | **`aggressive`** |
| Drink water before lunch | Health | 1:00 PM IST | `pending` | `silent` |
| Evening study block | Learning | 7:00 PM IST | `pending` | `standard` |

The two `aggressive` tasks are scheduled within 10–13 minutes of the script running so the notifier picks them up almost immediately.

### 4c. Future tasks (next 2 weeks)

~15 tasks spread across all 3 goals, all `pending`, `escalation_policy` mix of `silent`/`standard`.

---

## 5. Patterns

Five rows to make the patterns surface feel populated:

| `pattern_type` | `pattern_key` | Description | `confidence` |
|---|---|---|---|
| `category_performance` | `fitness_performance` | Fitness tasks: 68% completion rate | 0.92 |
| `category_performance` | `health_performance` | Health tasks: 74% completion rate | 0.88 |
| `category_performance` | `learning_performance` | Learning tasks: 80% completion rate | 0.85 |
| `time_avoidance` | `wednesday_afternoon` | Tends to miss tasks on Wed 14:00–16:00 | 0.82 |
| `completion_streak` | `current_streak` | Current streak 7 days, peak 12 days | 0.95 |

---

## 6. Truncation Strategy

**Both scripts follow the same order:**
1. Delete `auth.users` row where `email = 'demo@flux.com'`
   - SQL: `DELETE FROM auth.users WHERE email = 'demo@flux.com'`
   - Python: `supabase.auth.admin.list_users()` → find UID → `delete_user(uid)`
2. `DELETE FROM public.users WHERE email = 'demo@flux.com'` — CASCADE wipes goals, tasks, conversations, messages, patterns, notification_log, dispatch_log
3. Re-create auth user and all seed data
4. `REFRESH MATERIALIZED VIEW` — `user_weekly_stats`, `missed_by_category`, `activity_heatmap`

Step 2 is a safety net for both scripts; the auth trigger handles normal creation but cascades may not remove the `public.users` row if auth user deletion races with the trigger.

---

## 7. Dependencies

**seed-local.sql:** None beyond Docker + local Supabase running.

**seed-hosted.sh + seed_hosted.py:**
```
supabase>=2.0.0     # supabase-py (Admin SDK)
asyncpg>=0.29.0     # direct Postgres connection
python-dotenv>=1.0  # optional, bash handles .env loading
```

The bash script checks for these and exits with install instructions if missing.

---

## 8. Files to Create

| File | Purpose |
|---|---|
| `backend/scripts/seed-local.sql` | Raw SQL seed for local Supabase |
| `backend/scripts/seed-hosted.sh` | Bash entrypoint for hosted Supabase |
| `backend/scripts/seed_hosted.py` | Python seed logic for hosted Supabase |

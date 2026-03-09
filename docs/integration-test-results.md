# Integration Test Results — 2026-03-03

## Summary

**Result: 24/24 tests passing (16/16 on subsequent runs after onboarding completes)**

All phases verified end-to-end: Supabase → Auth → Backend → Analytics → CORS.

## Issues Found & Fixed

### 1. Supabase CLI version mismatch (conf.d crash loop)
- **Symptom:** DB container crash-looping with `could not open configuration directory "/etc/postgresql-custom/conf.d"`
- **Root cause:** Supabase CLI v2.22.12 with newer Postgres image expecting conf.d directory
- **Fix:** `docker run --rm -v supabase_config_Flux-Team-8:/mnt alpine mkdir -p /mnt/conf.d` + upgraded CLI to v2.75.0

### 2. No auth→public user sync trigger
- **Symptom:** `/account/me` returned "User not found" — user existed in `auth.users` but not `public.users`
- **Fix:** Created `handle_new_user()` trigger on `auth.users` that auto-inserts into `public.users` on signup. Persisted as migration `20260303130000_auth_user_sync_trigger.sql`.

### 3. Scheduler 500 on missing task
- **Symptom:** `POST /scheduler/suggest` with non-existent task ID returned 500 instead of 400
- **Root cause:** `maybe_single().execute()` returns `None` (not an APIResponse) when no rows found; code tried `.data` on `None`
- **Fix:** Added null guard in `scheduler_service.get_task_by_id()` and `get_user_profile()`

### 4. Integration test assertions mismatched backend schema
- **Symptom:** Test checked for `"streak"` in analytics overview; backend returns `"streak_days"`
- **Fix:** Updated assertion to check `"streak_days"`

### 5. Integration test used service_role key for auth API
- **Symptom:** Auth API expects anon key; service_role key happened to work but was semantically wrong
- **Fix:** Added `SUPABASE_ANON_KEY` constant; auth calls now use anon key

### 6. Seed data invalid UUIDs
- **Symptom:** `INSERT INTO messages` failed — `g1000000-...` is not a valid UUID (hex digits only)
- **Fix:** Changed `g1` prefix to `01` in all 7 message UUIDs

### 7. Seed path in config.toml
- **Symptom:** `supabase db reset` warned "no files matched pattern: supabase/seed.sql"
- **Fix:** Updated `sql_paths` to `["./scripts/seed_test_data.sql"]`

### 8. Scheduler service queried removed columns
- **Symptom:** `get_user_profile()` selected `name, preferences` — columns removed by schema cutover migration
- **Fix:** Updated to select `profile, notification_preferences`

## Test Breakdown (First Run — 24 tests)

| Phase | Tests | Result |
|-------|-------|--------|
| Connectivity | 2 | 2/2 |
| Auth | 1 | 1/1 |
| Account | 1 | 1/1 |
| Onboarding Chat | 8 | 8/8 |
| Goal Chat | 2 | 2/2 |
| Tasks | 1 | 1/1 |
| Scheduler | 1 | 1/1 |
| Analytics | 5 | 5/5 |
| CORS | 3 | 3/3 |

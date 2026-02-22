# Supabase Setup Guide for Flux

This guide sets up local Supabase for Flux with the **current canonical schema** from `flux-claude.md`.

## Prerequisites

- Docker Desktop running
- Supabase CLI installed (`brew install supabase/tap/supabase`)
- Project root: `Flux-Team-8`

## Quick Setup (Recommended)

From project root:

```bash
bash scripts/supabase_setup.sh
```

What this script does:

1. Verifies Docker and Supabase CLI
2. Starts local Supabase
3. Applies **all** SQL migrations in `supabase/migrations/` in order
4. Seeds test data from `supabase/scripts/seed_test_data.sql` if DB is empty

## Local Service Endpoints

```bash
supabase status
```

Typical local endpoints:

- Studio: `http://127.0.0.1:54323`
- API: `http://127.0.0.1:54321/rest/v1`
- DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- Mailpit: `http://127.0.0.1:54324`

## Canonical Database Objects

### Tables

- `users`
- `goals`
- `tasks`
- `patterns`
- `conversations`
- `notification_log`

### Materialized Views

- `user_weekly_stats`
- `missed_by_category`

### Legacy Objects Removed

- `milestones`
- `demo_flags`
- legacy enum types: `task_state`, `task_priority`, `trigger_type`

## Verify Schema Quickly

```bash
docker exec supabase_db_Flux-Team-8 psql -U postgres -d postgres -Atc \
"SELECT table_name FROM information_schema.tables WHERE table_schema='public' \
AND table_name IN ('users','goals','tasks','patterns','conversations','notification_log') ORDER BY 1;"
```

## SQL Utility Scripts

- `supabase/scripts/truncate_tables.sql` - truncate canonical tables
- `supabase/scripts/drop_tables.sql` - drop canonical tables and analytics views
- `supabase/scripts/seed_test_data.sql` - seed canonical test data
- `supabase/scripts/VALIDATION_CHECKLIST.md` - fresh-install and upgrade-path validation steps

## Resetting the Local Database

```bash
supabase db reset
```

This recreates local DB and reapplies migrations.

## Troubleshooting

### Docker connection errors

- Ensure Docker Desktop is running.
- Re-run:

```bash
docker info
```

### Supabase CLI missing

```bash
brew install supabase/tap/supabase
```

### Migration failures

1. Confirm migration files are present in `supabase/migrations/`.
2. Run:

```bash
supabase db reset
```

3. If needed, run validation SQL in `supabase/scripts/VALIDATION_CHECKLIST.md`.

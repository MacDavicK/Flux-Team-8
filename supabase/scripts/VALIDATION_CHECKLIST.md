# Flux-Claude Schema Cutover Validation Checklist

Use this checklist to validate both fresh installs and upgrade-path migrations.

## Fresh Install Validation

1. Apply migrations on a clean DB.
2. Verify canonical tables exist:
   - `users`
   - `goals`
   - `tasks`
   - `patterns`
   - `conversations`
   - `notification_log`
3. Verify legacy tables do not exist:
   - `milestones`
   - `demo_flags`
4. Verify constraints:
   - `goals.status` check
   - `tasks.status` check
   - `tasks.trigger_type` check
   - `conversations.context_type` check
   - `notification_log.channel` check
5. Verify indexes:
   - `idx_tasks_user_scheduled_status`
   - `idx_goals_parent_goal_id`
   - `idx_patterns_updated_at`
6. Verify RLS/policies exist for all user-data tables.
7. Verify materialized views:
   - `user_weekly_stats`
   - `missed_by_category`

## Upgrade Path Validation

1. Start from pre-cutover schema.
2. Apply `20260222120000_flux_claude_schema_cutover.sql`.
3. Verify task status mapping:
   - `scheduled -> pending`
   - `completed -> done`
   - `missed -> missed`
   - `drifted -> rescheduled`
4. Verify `tasks.start_time` data migrated to `tasks.scheduled_at`.
5. Verify conversation rows preserved with generated `langgraph_thread_id`.
6. Verify legacy enum types and legacy tables are removed.
7. Apply RLS and analytics migrations.
8. Run seed script and ensure inserts succeed against canonical schema.

## SQL Smoke Checks

```sql
-- canonical table list
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('users', 'goals', 'tasks', 'patterns', 'conversations', 'notification_log');

-- legacy table absence
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('milestones', 'demo_flags');

-- materialized views
SELECT matviewname
FROM pg_matviews
WHERE schemaname = 'public'
  AND matviewname IN ('user_weekly_stats', 'missed_by_category');
```

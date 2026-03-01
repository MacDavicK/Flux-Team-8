-- Drop all Flux-Claude canonical tables/views
-- Order matters: drop dependent objects first.

DROP MATERIALIZED VIEW IF EXISTS missed_by_category CASCADE;
DROP MATERIALIZED VIEW IF EXISTS user_weekly_stats CASCADE;

DROP TABLE IF EXISTS notification_log CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS patterns CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS goals CASCADE;
DROP TABLE IF EXISTS users CASCADE;

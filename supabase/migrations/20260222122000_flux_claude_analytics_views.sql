-- Flux-Claude analytics materialized views
-- Refresh cadence: hourly in MVP (manual job/cron).

DROP MATERIALIZED VIEW IF EXISTS user_weekly_stats;
CREATE MATERIALIZED VIEW user_weekly_stats AS
SELECT
  user_id,
  DATE_TRUNC('week', scheduled_at) AS week,
  COUNT(*) FILTER (WHERE status = 'done') AS completed,
  COUNT(*) AS total,
  ROUND(
    CASE
      WHEN COUNT(*) = 0 THEN 0
      ELSE (COUNT(*) FILTER (WHERE status = 'done')::numeric / COUNT(*)::numeric) * 100
    END,
    1
  ) AS completion_pct
FROM tasks
WHERE scheduled_at IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', scheduled_at);

CREATE INDEX IF NOT EXISTS idx_user_weekly_stats_user_week
  ON user_weekly_stats (user_id, week);

DROP MATERIALIZED VIEW IF EXISTS missed_by_category;
CREATE MATERIALIZED VIEW missed_by_category AS
SELECT
  t.user_id,
  g.class_tags,
  COUNT(*) FILTER (WHERE t.status = 'missed') AS missed_count,
  COUNT(*) AS total_count
FROM tasks t
LEFT JOIN goals g
  ON t.goal_id = g.id
GROUP BY t.user_id, g.class_tags;

CREATE INDEX IF NOT EXISTS idx_missed_by_category_user_tags
  ON missed_by_category (user_id, class_tags);

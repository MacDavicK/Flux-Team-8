-- Weekly completion rate per user
CREATE MATERIALIZED VIEW IF NOT EXISTS user_weekly_stats AS
SELECT
    user_id,
    DATE_TRUNC('week', scheduled_at) AS week,
    COUNT(*) FILTER (WHERE status = 'done')  AS completed,
    COUNT(*)                                  AS total,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'done')::numeric / NULLIF(COUNT(*), 0) * 100,
    1) AS completion_pct
FROM tasks
WHERE scheduled_at IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', scheduled_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_weekly_stats_user_week ON user_weekly_stats (user_id, week);

-- Missed tasks by goal category
CREATE MATERIALIZED VIEW IF NOT EXISTS missed_by_category AS
SELECT
    t.user_id,
    UNNEST(g.class_tags)                             AS category,
    COUNT(*) FILTER (WHERE t.status = 'missed')      AS missed_count,
    COUNT(*)                                          AS total_count
FROM tasks t
LEFT JOIN goals g ON t.goal_id = g.id
WHERE g.class_tags IS NOT NULL
GROUP BY t.user_id, UNNEST(g.class_tags);

CREATE UNIQUE INDEX IF NOT EXISTS idx_missed_by_category_user_cat ON missed_by_category (user_id, category);

-- Activity heatmap (daily task completion density)
CREATE MATERIALIZED VIEW IF NOT EXISTS activity_heatmap AS
SELECT
    user_id,
    DATE_TRUNC('day', scheduled_at) AS day,
    COUNT(*) FILTER (WHERE status = 'done') AS completed_count,
    COUNT(*) AS total_count
FROM tasks
WHERE scheduled_at IS NOT NULL
GROUP BY user_id, DATE_TRUNC('day', scheduled_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_heatmap_user_day ON activity_heatmap (user_id, day);

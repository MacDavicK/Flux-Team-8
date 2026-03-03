-- Analytics RPC functions for Flux (BE-3 · SCRUM-59)
-- Called via supabase.rpc() from the analytics service.
-- Materialized views (user_weekly_stats, missed_by_category) already exist
-- in migration 20260222122000 — do NOT recreate them here.

-- 1. calculate_streak: count consecutive days backwards from today
--    where the user completed at least one task.
CREATE OR REPLACE FUNCTION calculate_streak(p_user_id UUID)
RETURNS INT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  streak INT := 0;
  check_date DATE := CURRENT_DATE;
  has_done BOOLEAN;
BEGIN
  LOOP
    SELECT EXISTS (
      SELECT 1
      FROM tasks
      WHERE user_id = p_user_id
        AND status = 'done'
        AND DATE(scheduled_at) = check_date
    ) INTO has_done;

    IF NOT has_done THEN
      -- If today has no completions yet, skip to yesterday
      -- (user may not have finished today's tasks).
      -- Once we've counted at least one day, a gap breaks the streak.
      IF check_date < CURRENT_DATE OR streak > 0 THEN
        EXIT;
      END IF;
      check_date := check_date - 1;
      CONTINUE;
    END IF;

    streak := streak + 1;
    check_date := check_date - 1;
  END LOOP;

  RETURN streak;
END;
$$;

-- 2. daily_heatmap: returns daily done-task counts for last N days.
CREATE OR REPLACE FUNCTION daily_heatmap(p_user_id UUID, p_days INT DEFAULT 365)
RETURNS TABLE(day TEXT, done_count INT)
LANGUAGE sql
STABLE
AS $$
  SELECT
    TO_CHAR(DATE(scheduled_at), 'YYYY-MM-DD') AS day,
    COUNT(*)::INT AS done_count
  FROM tasks
  WHERE user_id = p_user_id
    AND status = 'done'
    AND scheduled_at >= (CURRENT_DATE - p_days)::timestamptz
  GROUP BY DATE(scheduled_at)
  ORDER BY DATE(scheduled_at);
$$;

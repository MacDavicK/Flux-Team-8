-- Prevent duplicate pipeline goal rows for the same user + pipeline_order.
-- Without this, ON CONFLICT DO NOTHING in goal_planner.py was a no-op (no unique
-- constraint existed), so each goal_planner re-run inserted duplicate pipeline rows.
--
-- Partial unique index: only enforces uniqueness among pipeline/active goals so that
-- completed/abandoned goals don't block future goals at the same pipeline_order.
--
-- Use ON CONFLICT (user_id, pipeline_order) WHERE status IN ('pipeline', 'active')
-- in goal_planner.py — named constraint form does not work with partial indexes.
CREATE UNIQUE INDEX IF NOT EXISTS goals_user_pipeline_order_unique
    ON goals (user_id, pipeline_order)
    WHERE status IN ('pipeline', 'active');

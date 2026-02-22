-- Migration: Allow conversations to exist before a goal is created
-- The goal planner flow creates a conversation first, then creates the goal
-- only after the user confirms the plan.
--
-- NOTE: This migration is a historical no-op against the current schema.
-- The conversations table (created in 20260213145903_create_mvp_tables.sql) never
-- included a goal_id column, so the guarded ALTER below never executes.
-- Kept for audit-trail completeness; safe to run repeatedly.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'conversations'
      AND column_name = 'goal_id'
  ) THEN
    ALTER TABLE conversations
      ALTER COLUMN goal_id DROP NOT NULL;
  END IF;
END $$;

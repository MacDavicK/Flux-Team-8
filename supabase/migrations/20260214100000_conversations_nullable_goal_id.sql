-- Migration: Allow conversations to exist before a goal is created
-- The goal planner flow creates a conversation first, then creates the goal
-- only after the user confirms the plan.

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

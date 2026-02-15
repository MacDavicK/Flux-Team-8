-- Migration: Allow conversations to exist before a goal is created
-- The goal planner flow creates a conversation first, then creates the goal
-- only after the user confirms the plan.

ALTER TABLE conversations
  ALTER COLUMN goal_id DROP NOT NULL;

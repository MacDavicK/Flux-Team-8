-- Add title column to conversations table.
-- Starts NULL; populated asynchronously by goal_planner once a goal is identified.
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title TEXT;

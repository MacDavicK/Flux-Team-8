-- Flux MVP Schema
-- Creates core tables: users, goals, milestones, tasks, conversations, demo_flags
-- Safe to re-run: uses IF NOT EXISTS guards throughout

-- Enum types (wrapped in DO blocks since CREATE TYPE has no IF NOT EXISTS)
DO $$ BEGIN
  CREATE TYPE task_state AS ENUM ('scheduled', 'drifted', 'completed', 'missed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE task_priority AS ENUM ('standard', 'important', 'must-not-miss');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE trigger_type AS ENUM ('time', 'on_leaving_home');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Users
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text UNIQUE NOT NULL,
  preferences jsonb DEFAULT '{}'::jsonb,
  demo_mode boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

-- Goals
CREATE TABLE IF NOT EXISTS goals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  title text NOT NULL,
  category text,
  timeline text,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals (user_id);

-- Milestones
CREATE TABLE IF NOT EXISTS milestones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  goal_id uuid NOT NULL REFERENCES goals (id) ON DELETE CASCADE,
  week_number integer NOT NULL,
  title text NOT NULL,
  status text DEFAULT 'pending',
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_milestones_goal_id ON milestones (goal_id);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  goal_id uuid NOT NULL REFERENCES goals (id) ON DELETE CASCADE,
  milestone_id uuid REFERENCES milestones (id) ON DELETE CASCADE,
  title text NOT NULL,
  start_time timestamptz,
  end_time timestamptz,
  state task_state DEFAULT 'scheduled',
  priority task_priority DEFAULT 'standard',
  trigger_type trigger_type DEFAULT 'time',
  is_recurring boolean DEFAULT false,
  calendar_event_id varchar(255),
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks (goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_milestone_id ON tasks (milestone_id);
CREATE INDEX IF NOT EXISTS idx_tasks_calendar_event_id ON tasks (calendar_event_id);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  goal_id uuid NOT NULL REFERENCES goals (id) ON DELETE CASCADE,
  messages jsonb DEFAULT '[]'::jsonb,
  status text DEFAULT 'open',
  created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_goal_id ON conversations (goal_id);

-- Demo flags (one row per user)
CREATE TABLE IF NOT EXISTS demo_flags (
  user_id uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  virtual_now timestamptz,
  escalation_speed float DEFAULT 1.0
);

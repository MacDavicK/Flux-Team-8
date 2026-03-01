-- Flux-Claude canonical schema
-- Source of truth: flux-claude.md
-- Safe to re-run in local environments via IF NOT EXISTS / guarded constraints.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now(),
  onboarded boolean DEFAULT false,
  profile jsonb,
  notification_preferences jsonb
);

-- Goals
CREATE TABLE IF NOT EXISTS goals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  title text NOT NULL,
  description text,
  class_tags text[],
  status text DEFAULT 'active',
  parent_goal_id uuid REFERENCES goals (id),
  pipeline_order int,
  created_at timestamptz DEFAULT now(),
  activated_at timestamptz,
  completed_at timestamptz,
  target_weeks int DEFAULT 6,
  plan_json jsonb
);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  goal_id uuid REFERENCES goals (id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  status text DEFAULT 'pending',
  scheduled_at timestamptz,
  duration_minutes int,
  trigger_type text DEFAULT 'time',
  location_trigger text,
  reminder_sent_at timestamptz,
  whatsapp_sent_at timestamptz,
  call_sent_at timestamptz,
  completed_at timestamptz,
  recurrence_rule text,
  shared_with_goal_ids uuid[],
  created_at timestamptz DEFAULT now()
);

-- Patterns
CREATE TABLE IF NOT EXISTS patterns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  pattern_type text,
  description text,
  data jsonb,
  confidence float,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION set_patterns_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_patterns_updated_at ON patterns;
CREATE TRIGGER trg_patterns_updated_at
BEFORE UPDATE ON patterns
FOR EACH ROW
EXECUTE FUNCTION set_patterns_updated_at();

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users (id),
  langgraph_thread_id text UNIQUE NOT NULL,
  context_type text NOT NULL,
  created_at timestamptz DEFAULT now(),
  last_message_at timestamptz
);

-- Notification log
CREATE TABLE IF NOT EXISTS notification_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id uuid NOT NULL REFERENCES tasks (id),
  channel text NOT NULL,
  sent_at timestamptz,
  response text,
  responded_at timestamptz
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'goals_status_check'
  ) THEN
    ALTER TABLE goals
      ADD CONSTRAINT goals_status_check
      CHECK (status IN ('active', 'completed', 'abandoned', 'pipeline'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'tasks_status_check'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_status_check
      CHECK (status IN ('pending', 'done', 'missed', 'rescheduled', 'cancelled'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'tasks_trigger_type_check'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_trigger_type_check
      CHECK (trigger_type IN ('time', 'location'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'conversations_context_type_check'
  ) THEN
    ALTER TABLE conversations
      ADD CONSTRAINT conversations_context_type_check
      CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'voice'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'notification_log_channel_check'
  ) THEN
    ALTER TABLE notification_log
      ADD CONSTRAINT notification_log_channel_check
      CHECK (channel IN ('push', 'whatsapp', 'call'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals (user_id);
CREATE INDEX IF NOT EXISTS idx_goals_parent_goal_id ON goals (parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals (status);
CREATE INDEX IF NOT EXISTS idx_goals_activated_at ON goals (activated_at);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks (goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder_sent_at ON tasks (reminder_sent_at);
CREATE INDEX IF NOT EXISTS idx_tasks_whatsapp_sent_at ON tasks (whatsapp_sent_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled_status ON tasks (user_id, scheduled_at, status);

CREATE INDEX IF NOT EXISTS idx_patterns_user_id ON patterns (user_id);
CREATE INDEX IF NOT EXISTS idx_patterns_pattern_type ON patterns (pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_updated_at ON patterns (updated_at);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations (last_message_at);

CREATE INDEX IF NOT EXISTS idx_notification_log_task_id ON notification_log (task_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log (sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_response ON notification_log (response);

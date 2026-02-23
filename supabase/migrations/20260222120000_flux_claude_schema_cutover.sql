-- Flux-Claude strict cutover migration
-- Transforms legacy MVP schema into the canonical schema described in flux-claude.md.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- USERS -----------------------------------------------------------------------
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS onboarded boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS profile jsonb,
  ADD COLUMN IF NOT EXISTS notification_preferences jsonb;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'name'
  ) THEN
    UPDATE users
    SET profile = COALESCE(
      profile,
      jsonb_build_object(
        'name', name,
        'legacy_preferences', COALESCE(preferences, '{}'::jsonb)
      )
    )
    WHERE profile IS NULL;
  END IF;
END $$;

UPDATE users
SET notification_preferences = COALESCE(
  notification_preferences,
  jsonb_build_object(
    'phone_number', NULL,
    'whatsapp_opted_in', false,
    'reminder_lead_minutes', 10,
    'escalation_window_minutes', 2
  )
)
WHERE notification_preferences IS NULL;

ALTER TABLE users
  DROP COLUMN IF EXISTS name,
  DROP COLUMN IF EXISTS preferences,
  DROP COLUMN IF EXISTS demo_mode;

-- GOALS -----------------------------------------------------------------------
ALTER TABLE goals
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS class_tags text[],
  ADD COLUMN IF NOT EXISTS parent_goal_id uuid,
  ADD COLUMN IF NOT EXISTS pipeline_order int,
  ADD COLUMN IF NOT EXISTS activated_at timestamptz,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS target_weeks int DEFAULT 6,
  ADD COLUMN IF NOT EXISTS plan_json jsonb;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'goals'
      AND column_name = 'category'
  ) THEN
    UPDATE goals
    SET class_tags = COALESCE(class_tags, ARRAY[INITCAP(category)]);
  END IF;
END $$;

ALTER TABLE goals
  DROP COLUMN IF EXISTS category,
  DROP COLUMN IF EXISTS timeline;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'goals_parent_goal_id_fkey'
  ) THEN
    ALTER TABLE goals
      ADD CONSTRAINT goals_parent_goal_id_fkey
      FOREIGN KEY (parent_goal_id) REFERENCES goals(id);
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'goals_status_check'
  ) THEN
    ALTER TABLE goals DROP CONSTRAINT goals_status_check;
  END IF;
END $$;

ALTER TABLE goals
  ADD CONSTRAINT goals_status_check
  CHECK (status IN ('active', 'completed', 'abandoned', 'pipeline'));

-- TASKS -----------------------------------------------------------------------
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS status text,
  ADD COLUMN IF NOT EXISTS scheduled_at timestamptz,
  ADD COLUMN IF NOT EXISTS duration_minutes int,
  ADD COLUMN IF NOT EXISTS location_trigger text,
  ADD COLUMN IF NOT EXISTS reminder_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS whatsapp_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS call_sent_at timestamptz,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS recurrence_rule text,
  ADD COLUMN IF NOT EXISTS shared_with_goal_ids uuid[];

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tasks' AND column_name = 'state'
  ) THEN
    UPDATE tasks
    SET status = CASE state::text
      WHEN 'scheduled' THEN 'pending'
      WHEN 'completed' THEN 'done'
      WHEN 'missed' THEN 'missed'
      WHEN 'drifted' THEN 'rescheduled'
      ELSE 'pending'
    END
    WHERE status IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tasks' AND column_name = 'start_time'
  ) THEN
    UPDATE tasks
    SET scheduled_at = COALESCE(scheduled_at, start_time)
    WHERE scheduled_at IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tasks' AND column_name = 'end_time'
  ) THEN
    UPDATE tasks
    SET duration_minutes = COALESCE(
      duration_minutes,
      GREATEST(
        1,
        FLOOR(EXTRACT(EPOCH FROM (end_time - start_time)) / 60)::int
      )
    )
    WHERE end_time IS NOT NULL
      AND start_time IS NOT NULL
      AND duration_minutes IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tasks' AND column_name = 'trigger_type'
  ) THEN
    -- Drop default first so old enum-typed default does not keep trigger_type alive.
    ALTER TABLE tasks
      ALTER COLUMN trigger_type DROP DEFAULT;

    ALTER TABLE tasks
      ALTER COLUMN trigger_type TYPE text
      USING CASE
        WHEN trigger_type::text = 'on_leaving_home' THEN 'location'
        ELSE trigger_type::text
      END;

    ALTER TABLE tasks
      ALTER COLUMN trigger_type SET DEFAULT 'time';
  END IF;
END $$;

UPDATE tasks
SET status = 'pending'
WHERE status IS NULL;

ALTER TABLE tasks
  ALTER COLUMN status SET DEFAULT 'pending';

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tasks'
      AND column_name = 'goal_id'
      AND is_nullable = 'NO'
  ) THEN
    ALTER TABLE tasks
      ALTER COLUMN goal_id DROP NOT NULL;
  END IF;
END $$;

ALTER TABLE tasks
  DROP CONSTRAINT IF EXISTS tasks_goal_id_fkey;

ALTER TABLE tasks
  ADD CONSTRAINT tasks_goal_id_fkey
  FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'tasks_status_check'
  ) THEN
    ALTER TABLE tasks DROP CONSTRAINT tasks_status_check;
  END IF;
END $$;

ALTER TABLE tasks
  ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('pending', 'done', 'missed', 'rescheduled', 'cancelled'));

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'tasks_trigger_type_check'
  ) THEN
    ALTER TABLE tasks DROP CONSTRAINT tasks_trigger_type_check;
  END IF;
END $$;

ALTER TABLE tasks
  ADD CONSTRAINT tasks_trigger_type_check
  CHECK (trigger_type IN ('time', 'location'));

ALTER TABLE tasks
  DROP COLUMN IF EXISTS milestone_id,
  DROP COLUMN IF EXISTS start_time,
  DROP COLUMN IF EXISTS end_time,
  DROP COLUMN IF EXISTS state,
  DROP COLUMN IF EXISTS priority,
  DROP COLUMN IF EXISTS is_recurring,
  DROP COLUMN IF EXISTS calendar_event_id;

-- CONVERSATIONS ----------------------------------------------------------------
ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS langgraph_thread_id text,
  ADD COLUMN IF NOT EXISTS context_type text,
  ADD COLUMN IF NOT EXISTS last_message_at timestamptz;

UPDATE conversations
SET langgraph_thread_id = COALESCE(langgraph_thread_id, 'legacy-' || id::text)
WHERE langgraph_thread_id IS NULL;

UPDATE conversations
SET context_type = COALESCE(context_type, 'goal')
WHERE context_type IS NULL;

UPDATE conversations
SET last_message_at = COALESCE(last_message_at, created_at)
WHERE last_message_at IS NULL;

ALTER TABLE conversations
  ALTER COLUMN langgraph_thread_id SET NOT NULL,
  ALTER COLUMN context_type SET NOT NULL;

ALTER TABLE conversations
  DROP COLUMN IF EXISTS goal_id,
  DROP COLUMN IF EXISTS messages,
  DROP COLUMN IF EXISTS status;

ALTER TABLE conversations
  DROP CONSTRAINT IF EXISTS conversations_user_id_fkey;

ALTER TABLE conversations
  ADD CONSTRAINT conversations_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES users(id);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'conversations_langgraph_thread_id_key'
  ) THEN
    ALTER TABLE conversations
      ADD CONSTRAINT conversations_langgraph_thread_id_key
      UNIQUE (langgraph_thread_id);
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'conversations_context_type_check'
  ) THEN
    ALTER TABLE conversations DROP CONSTRAINT conversations_context_type_check;
  END IF;
END $$;

ALTER TABLE conversations
  ADD CONSTRAINT conversations_context_type_check
  CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule'));

-- NEW TABLES -------------------------------------------------------------------
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
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'notification_log_channel_check'
  ) THEN
    ALTER TABLE notification_log DROP CONSTRAINT notification_log_channel_check;
  END IF;
END $$;

ALTER TABLE notification_log
  ADD CONSTRAINT notification_log_channel_check
  CHECK (channel IN ('push', 'whatsapp', 'call'));

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

-- Drop legacy structures --------------------------------------------------------
DROP TABLE IF EXISTS demo_flags CASCADE;
DROP TABLE IF EXISTS milestones CASCADE;

DROP TYPE IF EXISTS task_state;
DROP TYPE IF EXISTS task_priority;
DROP TYPE IF EXISTS trigger_type;

-- Indexes ----------------------------------------------------------------------
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

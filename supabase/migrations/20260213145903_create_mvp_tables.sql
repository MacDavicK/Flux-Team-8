-- Flux canonical schema — MVP tables + voice conversational agent support.
-- Safe to re-run in local environments: IF NOT EXISTS / guarded constraints.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── Users ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
  id                        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email                     text        UNIQUE NOT NULL,
  created_at                timestamptz DEFAULT now(),
  onboarded                 boolean     DEFAULT false,
  profile                   jsonb,
  notification_preferences  jsonb
);

-- ── Goals ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS goals (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  title            text        NOT NULL,
  description      text,
  class_tags       text[],
  status           text        DEFAULT 'active',
  parent_goal_id   uuid        REFERENCES goals (id),
  pipeline_order   int,
  created_at       timestamptz DEFAULT now(),
  activated_at     timestamptz,
  completed_at     timestamptz,
  target_weeks     int         DEFAULT 6,
  plan_json        jsonb
);

-- ── Tasks ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tasks (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  goal_id               uuid        REFERENCES goals (id) ON DELETE SET NULL,
  title                 text        NOT NULL,
  description           text,
  status                text        DEFAULT 'pending',
  scheduled_at          timestamptz,
  duration_minutes      int,
  trigger_type          text        DEFAULT 'time',
  location_trigger      text,
  reminder_sent_at      timestamptz,
  whatsapp_sent_at      timestamptz,
  call_sent_at          timestamptz,
  completed_at          timestamptz,
  recurrence_rule       text,
  shared_with_goal_ids  uuid[],
  created_at            timestamptz DEFAULT now()
);

-- ── Patterns ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS patterns (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  pattern_type  text,
  description   text,
  data          jsonb,
  confidence    float,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
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

-- ── Conversations ─────────────────────────────────────────────────────────────
-- Includes voice-session columns from the start.

CREATE TABLE IF NOT EXISTS conversations (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES users (id),
  langgraph_thread_id text        UNIQUE NOT NULL,
  context_type        text        NOT NULL,
  created_at          timestamptz DEFAULT now(),
  last_message_at     timestamptz,
  -- Voice session fields
  voice_session_id    text,
  extracted_intent    text,
  intent_payload      jsonb,
  linked_goal_id      uuid        REFERENCES goals (id),
  linked_task_id      uuid        REFERENCES tasks (id),
  ended_at            timestamptz,
  duration_seconds    int
);

-- ── Messages ──────────────────────────────────────────────────────────────────
-- Stores individual conversation turns (voice and text).

CREATE TABLE IF NOT EXISTS messages (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  uuid        NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
  role             text        NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'function')),
  content          text        NOT NULL,
  input_modality   text        NOT NULL DEFAULT 'text' CHECK (input_modality IN ('voice', 'text')),
  metadata         jsonb       DEFAULT '{}',
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- ── Notification log ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notification_log (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid        NOT NULL REFERENCES tasks (id),
  channel       text        NOT NULL,
  sent_at       timestamptz,
  response      text,
  responded_at  timestamptz
);

-- ── Check constraints (guarded so re-runs are safe) ──────────────────────────

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'goals_status_check'
  ) THEN
    ALTER TABLE goals
      ADD CONSTRAINT goals_status_check
      CHECK (status IN ('active', 'completed', 'abandoned', 'pipeline'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'tasks_status_check'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_status_check
      CHECK (status IN ('pending', 'done', 'missed', 'rescheduled', 'cancelled'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'tasks_trigger_type_check'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT tasks_trigger_type_check
      CHECK (trigger_type IN ('time', 'location'));
  END IF;
END $$;

DO $$
BEGIN
  -- Drop any legacy version of this constraint that lacks 'voice', then
  -- recreate with the full set so re-runs on existing databases always
  -- leave the constraint in the correct state.
  IF EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'conversations_context_type_check'
  ) THEN
    ALTER TABLE conversations DROP CONSTRAINT conversations_context_type_check;
  END IF;

  ALTER TABLE conversations
    ADD CONSTRAINT conversations_context_type_check
    CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'voice'));
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'notification_log_channel_check'
  ) THEN
    ALTER TABLE notification_log
      ADD CONSTRAINT notification_log_channel_check
      CHECK (channel IN ('push', 'whatsapp', 'call'));
  END IF;
END $$;

-- ── Voice columns: ensure they exist on older databases ──────────────────────
-- These ALTER TABLE statements are no-ops when the CREATE TABLE above ran
-- fresh, but they allow the script to upgrade a database that was created
-- before voice support was added.

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS voice_session_id  text;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS extracted_intent  text;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_payload    jsonb;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS linked_goal_id   uuid REFERENCES goals (id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS linked_task_id   uuid REFERENCES tasks (id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ended_at         timestamptz;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS duration_seconds int;

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_goals_user_id         ON goals (user_id);
CREATE INDEX IF NOT EXISTS idx_goals_parent_goal_id  ON goals (parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_status          ON goals (status);
CREATE INDEX IF NOT EXISTS idx_goals_activated_at    ON goals (activated_at);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id              ON tasks (user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id              ON tasks (goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status               ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at         ON tasks (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder_sent_at     ON tasks (reminder_sent_at);
CREATE INDEX IF NOT EXISTS idx_tasks_whatsapp_sent_at     ON tasks (whatsapp_sent_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled_status ON tasks (user_id, scheduled_at, status);

CREATE INDEX IF NOT EXISTS idx_patterns_user_id      ON patterns (user_id);
CREATE INDEX IF NOT EXISTS idx_patterns_pattern_type ON patterns (pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_updated_at   ON patterns (updated_at);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id        ON conversations (user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations (last_message_at);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_notification_log_task_id  ON notification_log (task_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at  ON notification_log (sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_response ON notification_log (response);

-- Migration: Voice conversational agent support
-- Adds messages table and extends conversations for voice sessions.

-- 1. messages table — stores individual conversation turns
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'function')),
    content         TEXT NOT NULL,
    input_modality  TEXT NOT NULL DEFAULT 'text' CHECK (input_modality IN ('voice', 'text')),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages(conversation_id, created_at);

-- 2. conversations table — add voice-specific columns
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS voice_session_id  TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS extracted_intent   TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_payload     JSONB;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS linked_goal_id     UUID REFERENCES goals(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS linked_task_id     UUID REFERENCES tasks(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ended_at           TIMESTAMPTZ;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS duration_seconds   INT;

-- 3. Expand context_type constraint to include 'voice'
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
  CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'voice'));

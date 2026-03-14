-- Link standalone tasks back to the conversation that created them.
-- This enables the task_handler to UPDATE an existing task when the user
-- amends it in the same conversation (e.g. "change that to every 20 minutes").
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id);

CREATE INDEX IF NOT EXISTS idx_tasks_conversation_id
    ON tasks (conversation_id)
    WHERE conversation_id IS NOT NULL;

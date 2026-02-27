-- tasks: Primary query patterns
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled     ON tasks (user_id, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status        ON tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id            ON tasks (goal_id) WHERE goal_id IS NOT NULL;

-- Partial indexes for notifier poll queries (critical for performance)
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_push      ON tasks (scheduled_at, reminder_sent_at, status)
    WHERE status = 'pending' AND reminder_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_whatsapp  ON tasks (reminder_sent_at, whatsapp_sent_at, status)
    WHERE status = 'pending' AND whatsapp_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_call      ON tasks (whatsapp_sent_at, call_sent_at, status)
    WHERE status = 'pending' AND call_sent_at IS NULL;

-- goals: User + status queries
CREATE INDEX IF NOT EXISTS idx_goals_user_status        ON goals (user_id, status);
CREATE INDEX IF NOT EXISTS idx_goals_parent             ON goals (parent_goal_id) WHERE parent_goal_id IS NOT NULL;

-- messages: Conversation history retrieval
CREATE INDEX IF NOT EXISTS idx_messages_conversation    ON messages (conversation_id, created_at);

-- patterns: User pattern lookup
CREATE INDEX IF NOT EXISTS idx_patterns_user_type       ON patterns (user_id, pattern_type);

-- notification_log: Idempotency lookup
CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_log_external_id ON notification_log (external_id)
    WHERE external_id IS NOT NULL;

-- dispatch_log: Recovery queries
CREATE INDEX IF NOT EXISTS idx_dispatch_log_pending     ON dispatch_log (status, created_at)
    WHERE status = 'pending';

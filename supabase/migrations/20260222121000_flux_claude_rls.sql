-- Flux-Claude RLS policies
-- Enables owner-scoped access for all user-data tables.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_owner_policy ON users;
CREATE POLICY users_owner_policy
ON users
FOR ALL
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS goals_owner_policy ON goals;
CREATE POLICY goals_owner_policy
ON goals
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS tasks_owner_policy ON tasks;
CREATE POLICY tasks_owner_policy
ON tasks
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS patterns_owner_policy ON patterns;
CREATE POLICY patterns_owner_policy
ON patterns
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS conversations_owner_policy ON conversations;
CREATE POLICY conversations_owner_policy
ON conversations
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS notification_log_owner_policy ON notification_log;
CREATE POLICY notification_log_owner_policy
ON notification_log
FOR ALL
USING (
  EXISTS (
    SELECT 1
    FROM tasks t
    WHERE t.id = notification_log.task_id
      AND t.user_id = auth.uid()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM tasks t
    WHERE t.id = notification_log.task_id
      AND t.user_id = auth.uid()
  )
);

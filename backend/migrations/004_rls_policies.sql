-- Enable RLS on all user-data tables
DO $$ BEGIN ALTER TABLE users             ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE goals             ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE tasks             ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE messages          ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE conversations     ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE patterns          ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE notification_log  ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE dispatch_log      ENABLE ROW LEVEL SECURITY; EXCEPTION WHEN others THEN NULL; END $$;

-- users: Can only read/write own row
DROP POLICY IF EXISTS users_self ON users;
CREATE POLICY users_self ON users
    USING (id = auth.uid());

-- goals: Own goals only
DROP POLICY IF EXISTS goals_owner ON goals;
CREATE POLICY goals_owner ON goals
    USING (user_id = auth.uid());

-- tasks: Own tasks only
DROP POLICY IF EXISTS tasks_owner ON tasks;
CREATE POLICY tasks_owner ON tasks
    USING (user_id = auth.uid());

-- messages: Via conversation ownership
DROP POLICY IF EXISTS messages_owner ON messages;
CREATE POLICY messages_owner ON messages
    USING (conversation_id IN (
        SELECT id FROM conversations WHERE user_id = auth.uid()
    ));

-- conversations: Own conversations only
DROP POLICY IF EXISTS conversations_owner ON conversations;
CREATE POLICY conversations_owner ON conversations
    USING (user_id = auth.uid());

-- patterns: Own patterns only
DROP POLICY IF EXISTS patterns_owner ON patterns;
CREATE POLICY patterns_owner ON patterns
    USING (user_id = auth.uid());

-- notification_log: Via task ownership
DROP POLICY IF EXISTS notification_log_owner ON notification_log;
CREATE POLICY notification_log_owner ON notification_log
    USING (task_id IN (
        SELECT id FROM tasks WHERE user_id = auth.uid()
    ));

-- dispatch_log: Via task ownership
DROP POLICY IF EXISTS dispatch_log_owner ON dispatch_log;
CREATE POLICY dispatch_log_owner ON dispatch_log
    USING (task_id IN (
        SELECT id FROM tasks WHERE user_id = auth.uid()
    ));

-- NOTE: The backend uses SUPABASE_SERVICE_ROLE_KEY for all server-side writes.
-- The service role bypasses RLS automatically — never expose it client-side.

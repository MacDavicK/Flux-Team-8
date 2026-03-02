-- ─────────────────────────────────────────────────────────────────────────────
-- 001_schema.sql  –  Flux canonical clean-slate schema
-- Single file: tables + indexes + materialized views + RLS + triggers + auth
-- Safe to run on a fresh database; idempotent on repeated runs.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── 1. Extension ─────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── 2. Tables ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   TEXT UNIQUE NOT NULL,
    created_at              TIMESTAMPTZ DEFAULT now(),
    onboarded               BOOLEAN DEFAULT false,
    timezone                TEXT NOT NULL DEFAULT 'UTC',        -- IANA timezone string e.g. 'Asia/Dubai'
    phone_verified          BOOLEAN DEFAULT false,
    whatsapp_opt_in_at      TIMESTAMPTZ,                       -- NULL = not opted in
    push_subscription       JSONB,                             -- Web Push subscription object
    profile                 JSONB,
    -- profile schema:
    -- {
    --   "name": "Alex",
    --   "sleep_window": { "start": "23:00", "end": "07:00" },
    --   "work_hours": { "start": "09:00", "end": "18:00", "days": ["Mon","Tue","Wed","Thu","Fri"] },
    --   "chronotype": "morning" | "evening" | "neutral",
    --   "existing_commitments": [
    --     { "title": "Gym", "days": ["Tuesday"], "time": "19:00", "duration_minutes": 60 }
    --   ],
    --   "locations": { "home": "labeled_home", "work": "labeled_work" }
    -- }
    notification_preferences JSONB DEFAULT '{
        "phone_number": null,
        "whatsapp_opted_in": false,
        "reminder_lead_minutes": 10,
        "escalation_window_minutes": 2
    }'::jsonb,
    monthly_token_usage     JSONB DEFAULT '{
        "openai": 0,
        "anthropic": 0,
        "total": 0,
        "reset_at": null
    }'::jsonb                                                  -- Token usage tracking for cost controls
);

CREATE TABLE IF NOT EXISTS goals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title                   TEXT NOT NULL,
    description             TEXT,
    class_tags              TEXT[] DEFAULT '{}',               -- ["Health", "Fitness"] from Classifier
    status                  TEXT NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active', 'completed', 'abandoned', 'pipeline')),
    parent_goal_id          UUID REFERENCES goals(id),         -- for micro-goal chains
    pipeline_order          INT,                               -- sequence within a micro-goal chain
    created_at              TIMESTAMPTZ DEFAULT now(),
    activated_at            TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    target_weeks            INT DEFAULT 6,
    plan_json               JSONB                              -- full negotiated plan snapshot
);

CREATE TABLE IF NOT EXISTS tasks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id                 UUID REFERENCES goals(id) ON DELETE SET NULL,
    title                   TEXT NOT NULL,
    description             TEXT,
    status                  TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'done', 'missed', 'rescheduled', 'cancelled')),
    scheduled_at            TIMESTAMPTZ,                       -- Always stored in UTC
    duration_minutes        INT,
    trigger_type            TEXT DEFAULT 'time'
                                CHECK (trigger_type IN ('time', 'location')),
    location_trigger        TEXT,                              -- e.g. "away_from_home" (MVP: simulated)
    recurrence_rule         TEXT,                              -- iCal RRULE string, RFC 5545
    shared_with_goal_ids    UUID[] DEFAULT '{}',               -- Task belongs to multiple goals
    -- Notification state tracking (atomic CAS update to prevent double-fire)
    reminder_sent_at        TIMESTAMPTZ,                       -- Push sent timestamp
    whatsapp_sent_at        TIMESTAMPTZ,                       -- WhatsApp sent timestamp
    call_sent_at            TIMESTAMPTZ,                       -- Voice call sent timestamp
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- conversations MUST be created before messages — FK dependency
CREATE TABLE IF NOT EXISTS conversations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    langgraph_thread_id     TEXT UNIQUE NOT NULL,
    context_type            TEXT CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'voice', 'general')),
    created_at              TIMESTAMPTZ DEFAULT now(),
    last_message_at         TIMESTAMPTZ,
    -- Voice session fields
    voice_session_id        TEXT,
    extracted_intent        TEXT,
    intent_payload          JSONB,
    linked_goal_id          UUID REFERENCES goals(id),
    linked_task_id          UUID REFERENCES tasks(id),
    ended_at                TIMESTAMPTZ,
    duration_seconds        INT
);

CREATE TABLE IF NOT EXISTS messages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id         UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                    TEXT NOT NULL
                                CHECK (role IN ('user', 'assistant', 'system', 'function', 'summary')),
    content                 TEXT NOT NULL,
    input_modality          TEXT NOT NULL DEFAULT 'text'
                                CHECK (input_modality IN ('voice', 'text')),
    metadata                JSONB DEFAULT '{}',
    agent_node              TEXT,                              -- which agent produced this message
    tokens_used             INT DEFAULT 0,
    provider                TEXT,                              -- 'openai' | 'anthropic'
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS patterns (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pattern_type            TEXT NOT NULL,                     -- 'time_avoidance' | 'completion_streak' | 'category_performance'
    description             TEXT,                              -- Human-readable summary
    data                    JSONB,                             -- Raw signal data
    confidence              FLOAT CHECK (confidence BETWEEN 0.0 AND 1.0),
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL CHECK (channel IN ('push', 'whatsapp', 'call')),
    external_id             TEXT,                              -- Twilio MessageSid or CallSid (idempotency key)
    sent_at                 TIMESTAMPTZ DEFAULT now(),
    response                TEXT CHECK (response IN ('done', 'reschedule', 'missed', 'no_response')),
    responded_at            TIMESTAMPTZ
);

-- dispatch_log  (idempotency + recovery for Notifier)
CREATE TABLE IF NOT EXISTS dispatch_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL CHECK (channel IN ('push', 'whatsapp', 'call', 'auto_miss')),
    status                  TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'dispatched', 'failed')),
    created_at              TIMESTAMPTZ DEFAULT now(),
    dispatched_at           TIMESTAMPTZ,
    error                   TEXT
);

-- ── 3. Indexes ────────────────────────────────────────────────────────────────

-- tasks: Composite query patterns
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled        ON tasks (user_id, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status           ON tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled_status ON tasks (user_id, scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id               ON tasks (goal_id) WHERE goal_id IS NOT NULL;

-- tasks: Single-column indexes (analytics / notifier)
CREATE INDEX IF NOT EXISTS idx_tasks_status                ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at          ON tasks (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_tasks_reminder_sent_at      ON tasks (reminder_sent_at);
CREATE INDEX IF NOT EXISTS idx_tasks_whatsapp_sent_at      ON tasks (whatsapp_sent_at);

-- tasks: Partial indexes for notifier poll queries (critical for performance)
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_push         ON tasks (scheduled_at, reminder_sent_at, status)
    WHERE status = 'pending' AND reminder_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_whatsapp     ON tasks (reminder_sent_at, whatsapp_sent_at, status)
    WHERE status = 'pending' AND whatsapp_sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_notifier_call         ON tasks (whatsapp_sent_at, call_sent_at, status)
    WHERE status = 'pending' AND call_sent_at IS NULL;

-- goals
CREATE INDEX IF NOT EXISTS idx_goals_user_status           ON goals (user_id, status);
CREATE INDEX IF NOT EXISTS idx_goals_parent                ON goals (parent_goal_id) WHERE parent_goal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_goals_status                ON goals (status);
CREATE INDEX IF NOT EXISTS idx_goals_activated_at          ON goals (activated_at);

-- conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_id          ON conversations (user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at  ON conversations (last_message_at);

-- messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation       ON messages (conversation_id, created_at);

-- patterns
CREATE INDEX IF NOT EXISTS idx_patterns_user_type          ON patterns (user_id, pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_pattern_type       ON patterns (pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_updated_at         ON patterns (updated_at);

-- notification_log
CREATE INDEX IF NOT EXISTS idx_notification_log_task_id    ON notification_log (task_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at    ON notification_log (sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_log_response   ON notification_log (response);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_log_external_id ON notification_log (external_id)
    WHERE external_id IS NOT NULL;

-- dispatch_log
CREATE INDEX IF NOT EXISTS idx_dispatch_log_pending        ON dispatch_log (status, created_at)
    WHERE status = 'pending';

-- ── 4. Materialized views ─────────────────────────────────────────────────────

-- Weekly completion rate per user
CREATE MATERIALIZED VIEW IF NOT EXISTS user_weekly_stats AS
SELECT
    user_id,
    DATE_TRUNC('week', scheduled_at) AS week,
    COUNT(*) FILTER (WHERE status = 'done')  AS completed,
    COUNT(*)                                  AS total,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'done')::numeric / NULLIF(COUNT(*), 0) * 100,
    1) AS completion_pct
FROM tasks
WHERE scheduled_at IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', scheduled_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_weekly_stats_user_week ON user_weekly_stats (user_id, week);

-- Missed tasks by goal category
CREATE MATERIALIZED VIEW IF NOT EXISTS missed_by_category AS
SELECT
    t.user_id,
    UNNEST(g.class_tags)                             AS category,
    COUNT(*) FILTER (WHERE t.status = 'missed')      AS missed_count,
    COUNT(*)                                          AS total_count
FROM tasks t
LEFT JOIN goals g ON t.goal_id = g.id
WHERE g.class_tags IS NOT NULL
GROUP BY t.user_id, UNNEST(g.class_tags);

CREATE UNIQUE INDEX IF NOT EXISTS idx_missed_by_category_user_cat ON missed_by_category (user_id, category);

-- Activity heatmap (daily task completion density)
CREATE MATERIALIZED VIEW IF NOT EXISTS activity_heatmap AS
SELECT
    user_id,
    DATE_TRUNC('day', scheduled_at) AS day,
    COUNT(*) FILTER (WHERE status = 'done') AS completed_count,
    COUNT(*) AS total_count
FROM tasks
WHERE scheduled_at IS NOT NULL
GROUP BY user_id, DATE_TRUNC('day', scheduled_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_activity_heatmap_user_day ON activity_heatmap (user_id, day);

-- ── 5. RLS policies ───────────────────────────────────────────────────────────

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

-- ── 6. Triggers ───────────────────────────────────────────────────────────────

-- Auto-refresh materialized views on task status update
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_weekly_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY missed_by_category;
    REFRESH MATERIALIZED VIEW CONCURRENTLY activity_heatmap;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_refresh_analytics ON tasks;
CREATE TRIGGER trigger_refresh_analytics
    AFTER UPDATE OF status ON tasks
    FOR EACH STATEMENT
    EXECUTE FUNCTION refresh_analytics_views();

-- Auto-update patterns.updated_at
CREATE OR REPLACE FUNCTION update_patterns_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_patterns_updated_at ON patterns;
CREATE TRIGGER trigger_patterns_updated_at
    BEFORE UPDATE ON patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_patterns_timestamp();

-- ── 7. Auth trigger ───────────────────────────────────────────────────────────

-- Auto-create public.users row when Supabase Auth creates a new user
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    _name TEXT;
BEGIN
    _name := NEW.raw_user_meta_data->>'name';
    INSERT INTO public.users (id, email, profile)
    VALUES (
        NEW.id,
        NEW.email,
        CASE WHEN _name IS NOT NULL AND _name <> ''
            THEN jsonb_build_object('name', _name)
            ELSE NULL
        END
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

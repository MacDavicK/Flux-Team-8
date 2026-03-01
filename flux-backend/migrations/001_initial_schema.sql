-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────────
-- users
-- ─────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────
-- goals
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS goals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title                   TEXT NOT NULL,
    description             TEXT,
    class_tags              TEXT[] DEFAULT '{}',               -- ["Health", "Fitness"] from Classifier
    status                  TEXT NOT NULL CHECK (status IN ('active', 'completed', 'abandoned', 'pipeline')),
    parent_goal_id          UUID REFERENCES goals(id),         -- for micro-goal chains
    pipeline_order          INT,                               -- sequence within a micro-goal chain
    created_at              TIMESTAMPTZ DEFAULT now(),
    activated_at            TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    target_weeks            INT DEFAULT 6,
    plan_json               JSONB                              -- full negotiated plan snapshot
);

-- ─────────────────────────────────────────────────────────────────
-- tasks
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id                 UUID REFERENCES goals(id),         -- NULL for standalone tasks
    title                   TEXT NOT NULL,
    description             TEXT,
    status                  TEXT NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'done', 'missed', 'rescheduled', 'cancelled')),
    scheduled_at            TIMESTAMPTZ,                       -- Always stored in UTC
    duration_minutes        INT,
    trigger_type            TEXT CHECK (trigger_type IN ('time', 'location')),
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

-- ─────────────────────────────────────────────────────────────────
-- conversations  (MUST be created before messages — FK dependency)
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    langgraph_thread_id     TEXT UNIQUE NOT NULL,
    context_type            TEXT CHECK (context_type IN ('onboarding', 'goal', 'task', 'reschedule', 'general')),
    created_at              TIMESTAMPTZ DEFAULT now(),
    last_message_at         TIMESTAMPTZ
);

-- ─────────────────────────────────────────────────────────────────
-- messages
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id         UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                    TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'summary')),
    content                 TEXT NOT NULL,
    agent_node              TEXT,                              -- which agent produced this message
    tokens_used             INT DEFAULT 0,
    provider                TEXT,                              -- 'openai' | 'anthropic'
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────
-- patterns
-- ─────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────
-- notification_log
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notification_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    channel                 TEXT NOT NULL CHECK (channel IN ('push', 'whatsapp', 'call')),
    external_id             TEXT,                              -- Twilio MessageSid or CallSid (idempotency key)
    sent_at                 TIMESTAMPTZ DEFAULT now(),
    response                TEXT CHECK (response IN ('done', 'reschedule', 'missed', 'no_response')),
    responded_at            TIMESTAMPTZ
);

-- ─────────────────────────────────────────────────────────────────
-- dispatch_log  (idempotency + recovery for Notifier)
-- ─────────────────────────────────────────────────────────────────
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

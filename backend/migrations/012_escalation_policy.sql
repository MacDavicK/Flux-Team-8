-- 012 — Add escalation_policy to tasks
-- Controls which notification channels fire for a given task.
-- silent: push only | standard: push + WhatsApp | aggressive: push + WhatsApp + call

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS escalation_policy TEXT NOT NULL DEFAULT 'standard'
        CHECK (escalation_policy IN ('silent', 'standard', 'aggressive'));

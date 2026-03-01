-- Flux-Claude test/seed data
-- Inserts sample data across canonical tables.

-- Users
INSERT INTO users (id, email, onboarded, profile, notification_preferences) VALUES
  (
    'a1000000-0000-0000-0000-000000000001',
    'alice@example.com',
    true,
    '{
      "name": "Alice Johnson",
      "sleep_window": {"start": "23:00", "end": "07:00"},
      "work_hours": {"start": "09:00", "end": "18:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]},
      "chronotype": "morning",
      "existing_commitments": [],
      "locations": {"home": "labeled_home", "work": "labeled_work"}
    }'::jsonb,
    '{"phone_number": "+15550000001", "whatsapp_opted_in": true, "reminder_lead_minutes": 10, "escalation_window_minutes": 2}'::jsonb
  ),
  (
    'a1000000-0000-0000-0000-000000000002',
    'bob@example.com',
    true,
    '{
      "name": "Bob Smith",
      "sleep_window": {"start": "00:00", "end": "08:00"},
      "work_hours": {"start": "10:00", "end": "19:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]},
      "chronotype": "evening",
      "existing_commitments": [{"title": "Gym", "days": ["Tuesday"], "time": "19:00", "duration_minutes": 60}],
      "locations": {"home": "labeled_home", "work": "labeled_work"}
    }'::jsonb,
    '{"phone_number": "+15550000002", "whatsapp_opted_in": false, "reminder_lead_minutes": 15, "escalation_window_minutes": 2}'::jsonb
  ),
  (
    'a1000000-0000-0000-0000-000000000003',
    'carol@example.com',
    false,
    NULL,
    '{"phone_number": null, "whatsapp_opted_in": false, "reminder_lead_minutes": 10, "escalation_window_minutes": 2}'::jsonb
  );

-- Goals (includes pipeline micro-goal example)
INSERT INTO goals (
  id, user_id, title, description, class_tags, status,
  parent_goal_id, pipeline_order, activated_at, completed_at, target_weeks, plan_json
) VALUES
  (
    'b1000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',
    'Run a half marathon',
    'Primary six-week sprint focused on consistent running volume.',
    ARRAY['Health', 'Fitness'],
    'active',
    NULL,
    NULL,
    now(),
    NULL,
    6,
    '{"summary": "3 runs/week with progressive overload"}'::jsonb
  ),
  (
    'b1000000-0000-0000-0000-000000000002',
    'a1000000-0000-0000-0000-000000000001',
    'Run a full marathon',
    'Second sprint, activated after half marathon completion.',
    ARRAY['Health', 'Fitness'],
    'pipeline',
    'b1000000-0000-0000-0000-000000000001',
    2,
    NULL,
    NULL,
    6,
    '{"summary": "Build toward marathon long-run capacity"}'::jsonb
  ),
  (
    'b1000000-0000-0000-0000-000000000003',
    'a1000000-0000-0000-0000-000000000002',
    'Ship MVP side project',
    'Deliver auth + CRUD in six weeks.',
    ARRAY['Career', 'Productivity'],
    'active',
    NULL,
    NULL,
    now(),
    NULL,
    6,
    '{"summary": "Weekly shipping milestones with daily coding blocks"}'::jsonb
  );

-- Tasks (goal-linked and standalone)
INSERT INTO tasks (
  id, user_id, goal_id, title, description, status, scheduled_at, duration_minutes,
  trigger_type, location_trigger, reminder_sent_at, whatsapp_sent_at, call_sent_at,
  completed_at, recurrence_rule, shared_with_goal_ids
) VALUES
  (
    'd1000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',
    'b1000000-0000-0000-0000-000000000001',
    'Morning run',
    'Easy run to build aerobic base.',
    'pending',
    now() + interval '1 hour',
    45,
    'time',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    'FREQ=WEEKLY;BYDAY=MO,WE,FR',
    NULL
  ),
  (
    'd1000000-0000-0000-0000-000000000002',
    'a1000000-0000-0000-0000-000000000001',
    NULL,
    'Buy groceries when away from home',
    'Standalone location-triggered reminder.',
    'rescheduled',
    NULL,
    20,
    'location',
    'away_from_home',
    now() - interval '4 hours',
    now() - interval '2 hours',
    NULL,
    NULL,
    NULL,
    NULL
  ),
  (
    'd1000000-0000-0000-0000-000000000003',
    'a1000000-0000-0000-0000-000000000002',
    'b1000000-0000-0000-0000-000000000003',
    'Code API endpoints',
    'Implement and test task APIs.',
    'done',
    now() - interval '1 day',
    90,
    'time',
    NULL,
    now() - interval '1 day 2 hours',
    NULL,
    NULL,
    now() - interval '22 hours',
    NULL,
    ARRAY['b1000000-0000-0000-0000-000000000003']::uuid[]
  ),
  (
    'd1000000-0000-0000-0000-000000000004',
    'a1000000-0000-0000-0000-000000000003',
    NULL,
    'Evening reading',
    'Read at least 20 pages.',
    'missed',
    now() - interval '3 hours',
    30,
    'time',
    NULL,
    now() - interval '3 hours 10 minutes',
    now() - interval '3 hours 7 minutes',
    now() - interval '3 hours 5 minutes',
    NULL,
    'FREQ=DAILY',
    NULL
  );

-- Patterns
INSERT INTO patterns (id, user_id, pattern_type, description, data, confidence, updated_at) VALUES
  (
    'f1000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',
    'completion_streak',
    'User completes morning tasks at high rate.',
    '{"best_times": ["07:00-09:00"], "sample_size": 12}'::jsonb,
    0.82,
    now()
  ),
  (
    'f1000000-0000-0000-0000-000000000002',
    'a1000000-0000-0000-0000-000000000003',
    'time_avoidance',
    'User repeatedly misses late-night tasks.',
    '{"avoid_slots": [{"day": "Mon", "time_range": "21:00-23:00"}], "sample_size": 4}'::jsonb,
    0.71,
    now()
  );

-- Conversations
INSERT INTO conversations (
  id, user_id, langgraph_thread_id, context_type, created_at, last_message_at,
  voice_session_id, extracted_intent, intent_payload, linked_goal_id, linked_task_id,
  ended_at, duration_seconds
) VALUES
  (
    'e1000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',
    'thread-alice-goal-1',
    'goal',
    now() - interval '2 days',
    now() - interval '1 day',
    NULL, NULL, NULL, NULL, NULL, NULL, NULL
  ),
  (
    'e1000000-0000-0000-0000-000000000002',
    'a1000000-0000-0000-0000-000000000002',
    'thread-bob-task-1',
    'task',
    now() - interval '1 day',
    now() - interval '3 hours',
    NULL, NULL, NULL, NULL, NULL, NULL, NULL
  ),
  (
    'e1000000-0000-0000-0000-000000000003',
    'a1000000-0000-0000-0000-000000000003',
    'thread-carol-onboarding-1',
    'onboarding',
    now() - interval '3 hours',
    now() - interval '1 hour',
    NULL, NULL, NULL, NULL, NULL, NULL, NULL
  ),
  (
    'e1000000-0000-0000-0000-000000000004',
    'a1000000-0000-0000-0000-000000000001',
    'thread-alice-voice-1',
    'voice',
    now() - interval '30 minutes',
    now() - interval '5 minutes',
    'vs_alice_20260301_001',
    'reschedule_task',
    '{"task_id": "d1000000-0000-0000-0000-000000000001", "new_time": "08:00"}'::jsonb,
    'b1000000-0000-0000-0000-000000000001',
    'd1000000-0000-0000-0000-000000000001',
    now() - interval '5 minutes',
    1520
  );

-- Messages
INSERT INTO messages (id, conversation_id, role, content, input_modality, metadata, created_at) VALUES
  -- Text messages in Alice's goal conversation
  (
    'g1000000-0000-0000-0000-000000000001',
    'e1000000-0000-0000-0000-000000000001',
    'user',
    'How is my half marathon goal progressing?',
    'text',
    '{}'::jsonb,
    now() - interval '2 days'
  ),
  (
    'g1000000-0000-0000-0000-000000000002',
    'e1000000-0000-0000-0000-000000000001',
    'assistant',
    'You''re on track! You''ve completed 3 of 6 planned runs this week.',
    'text',
    '{}'::jsonb,
    now() - interval '1 day 23 hours'
  ),
  -- Text messages in Bob's task conversation
  (
    'g1000000-0000-0000-0000-000000000003',
    'e1000000-0000-0000-0000-000000000002',
    'user',
    'Can you reschedule my API coding task to tomorrow morning?',
    'text',
    '{}'::jsonb,
    now() - interval '1 day'
  ),
  (
    'g1000000-0000-0000-0000-000000000004',
    'e1000000-0000-0000-0000-000000000002',
    'assistant',
    'Done! I''ve moved "Code API endpoints" to tomorrow at 09:00.',
    'text',
    '{}'::jsonb,
    now() - interval '23 hours'
  ),
  -- Voice messages in Alice's voice session
  (
    'g1000000-0000-0000-0000-000000000005',
    'e1000000-0000-0000-0000-000000000004',
    'user',
    'Hey, can you move my morning run to 8am instead?',
    'voice',
    '{"confidence": 0.97, "duration_ms": 2800}'::jsonb,
    now() - interval '28 minutes'
  ),
  (
    'g1000000-0000-0000-0000-000000000006',
    'e1000000-0000-0000-0000-000000000004',
    'assistant',
    'Sure! I''ve rescheduled your morning run to 8:00 AM. Anything else?',
    'voice',
    '{"tts_latency_ms": 340}'::jsonb,
    now() - interval '27 minutes 30 seconds'
  ),
  (
    'g1000000-0000-0000-0000-000000000007',
    'e1000000-0000-0000-0000-000000000004',
    'user',
    'No, that''s all. Thanks!',
    'voice',
    '{"confidence": 0.99, "duration_ms": 1100}'::jsonb,
    now() - interval '6 minutes'
  );

-- Notification log
INSERT INTO notification_log (id, task_id, channel, sent_at, response, responded_at) VALUES
  (
    'c1000000-0000-0000-0000-000000000001',
    'd1000000-0000-0000-0000-000000000004',
    'push',
    now() - interval '3 hours 10 minutes',
    'no_response',
    NULL
  ),
  (
    'c1000000-0000-0000-0000-000000000002',
    'd1000000-0000-0000-0000-000000000004',
    'whatsapp',
    now() - interval '3 hours 7 minutes',
    'missed',
    now() - interval '3 hours 6 minutes'
  ),
  (
    'c1000000-0000-0000-0000-000000000003',
    'd1000000-0000-0000-0000-000000000003',
    'push',
    now() - interval '1 day 2 hours',
    'done',
    now() - interval '1 day 1 hour 55 minutes'
  );

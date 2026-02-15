-- Flux MVP test/seed data
-- Inserts sample data across all 6 tables for local development

-- Users
INSERT INTO users (id, name, email, preferences, demo_mode) VALUES
  ('a1000000-0000-0000-0000-000000000001', 'Alice Johnson', 'alice@example.com', '{"theme": "dark", "notifications": true}'::jsonb, false),
  ('a1000000-0000-0000-0000-000000000002', 'Bob Smith', 'bob@example.com', '{"theme": "light", "notifications": false}'::jsonb, true),
  ('a1000000-0000-0000-0000-000000000003', 'Carol Lee', 'carol@example.com', '{}'::jsonb, false);

-- Goals
INSERT INTO goals (id, user_id, title, category, timeline, status) VALUES
  ('b1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'Run a half marathon', 'fitness', '12 weeks', 'active'),
  ('b1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'Learn Spanish basics', 'learning', '8 weeks', 'active'),
  ('b1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000002', 'Ship MVP side project', 'career', '6 weeks', 'active'),
  ('b1000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000003', 'Read 12 books this quarter', 'personal', '12 weeks', 'active');

-- Milestones
INSERT INTO milestones (id, goal_id, week_number, title, status) VALUES
  ('c1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001', 1, 'Run 5K without stopping', 'completed'),
  ('c1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000001', 4, 'Run 10K under 60 min', 'pending'),
  ('c1000000-0000-0000-0000-000000000003', 'b1000000-0000-0000-0000-000000000001', 12, 'Complete half marathon', 'pending'),
  ('c1000000-0000-0000-0000-000000000004', 'b1000000-0000-0000-0000-000000000002', 1, 'Learn 50 common words', 'completed'),
  ('c1000000-0000-0000-0000-000000000005', 'b1000000-0000-0000-0000-000000000002', 4, 'Hold a 2-min conversation', 'pending'),
  ('c1000000-0000-0000-0000-000000000006', 'b1000000-0000-0000-0000-000000000003', 1, 'Wireframes complete', 'completed'),
  ('c1000000-0000-0000-0000-000000000007', 'b1000000-0000-0000-0000-000000000003', 3, 'Backend API working', 'pending'),
  ('c1000000-0000-0000-0000-000000000008', 'b1000000-0000-0000-0000-000000000004', 4, 'Finish 4 books', 'pending');

-- Tasks (calendar_event_id is nullable — only set for tasks synced to external calendar)
INSERT INTO tasks (id, user_id, goal_id, milestone_id, title, start_time, end_time, state, priority, trigger_type, is_recurring, calendar_event_id) VALUES
  ('d1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001', 'c1000000-0000-0000-0000-000000000002', 'Morning run — 7K', '2026-02-14 06:30:00+00', '2026-02-14 07:15:00+00', 'scheduled', 'important', 'time', true, 'gcal-evt-run-001'),
  ('d1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000002', 'c1000000-0000-0000-0000-000000000005', 'Duolingo Spanish lesson', '2026-02-14 12:00:00+00', '2026-02-14 12:20:00+00', 'scheduled', 'standard', 'time', true, NULL),
  ('d1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001', 'c1000000-0000-0000-0000-000000000001', 'Stretch after run', '2026-02-13 07:15:00+00', '2026-02-13 07:30:00+00', 'completed', 'standard', 'time', false, NULL),
  ('d1000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000003', 'c1000000-0000-0000-0000-000000000007', 'Code API endpoints', '2026-02-14 10:00:00+00', '2026-02-14 12:00:00+00', 'scheduled', 'must-not-miss', 'time', false, 'gcal-evt-code-004'),
  ('d1000000-0000-0000-0000-000000000005', 'a1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000003', NULL, 'Review PR feedback', '2026-02-14 14:00:00+00', '2026-02-14 14:30:00+00', 'scheduled', 'standard', 'time', false, NULL),
  ('d1000000-0000-0000-0000-000000000006', 'a1000000-0000-0000-0000-000000000003', 'b1000000-0000-0000-0000-000000000004', 'c1000000-0000-0000-0000-000000000008', 'Read 30 pages', '2026-02-14 21:00:00+00', '2026-02-14 22:00:00+00', 'scheduled', 'standard', 'time', true, NULL),
  ('d1000000-0000-0000-0000-000000000007', 'a1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001', 'c1000000-0000-0000-0000-000000000002', 'Pack gym bag before leaving', NULL, NULL, 'drifted', 'important', 'on_leaving_home', false, NULL);

-- Conversations
INSERT INTO conversations (id, user_id, goal_id, messages, status) VALUES
  ('e1000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001', 'b1000000-0000-0000-0000-000000000001',
   '[{"role": "assistant", "text": "Great job finishing your 5K milestone! Ready to ramp up to 10K?"}, {"role": "user", "text": "Yes, but my knee has been sore."},{"role": "assistant", "text": "Let''s add a rest day and some stretching. I''ll adjust your schedule."}]'::jsonb,
   'open'),
  ('e1000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000002', 'b1000000-0000-0000-0000-000000000003',
   '[{"role": "assistant", "text": "Your wireframes milestone is done! Next up: backend API. Want to break it into sub-tasks?"}, {"role": "user", "text": "Sure, let''s do auth first then CRUD endpoints."}]'::jsonb,
   'open'),
  ('e1000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000003', 'b1000000-0000-0000-0000-000000000004',
   '[{"role": "assistant", "text": "You missed your reading session last night. Want to reschedule?"}]'::jsonb,
   'open');

-- Demo flags (Bob is in demo mode)
INSERT INTO demo_flags (user_id, virtual_now, escalation_speed) VALUES
  ('a1000000-0000-0000-0000-000000000002', '2026-02-14 09:00:00+00', 2.0);

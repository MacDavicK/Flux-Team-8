# Database Schema

Flux uses PostgreSQL via Supabase. Schema is defined in [supabase/migrations/20260213145903_create_mvp_tables.sql](../supabase/migrations/20260213145903_create_mvp_tables.sql). A follow-up migration ([20260214100000_conversations_nullable_goal_id.sql](../supabase/migrations/20260214100000_conversations_nullable_goal_id.sql)) makes `conversations.goal_id` nullable so conversations can be created before a goal exists.

---

## Enum types

| Type | Values |
|------|--------|
| `task_state` | `scheduled`, `drifted`, `completed`, `missed` |
| `task_priority` | `standard`, `important`, `must-not-miss` |
| `trigger_type` | `time`, `on_leaving_home` |

---

## Tables

### `users`

User profiles and preferences.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK, default `gen_random_uuid()` |
| `name` | text | NOT NULL |
| `email` | text | NOT NULL, UNIQUE |
| `preferences` | jsonb | default `{}` |
| `demo_mode` | boolean | default false |
| `created_at` | timestamptz | default now() |

### `goals`

User goals with category and timeline.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | uuid | FK → users, ON DELETE CASCADE |
| `title` | text | NOT NULL |
| `category` | text | |
| `timeline` | text | |
| `status` | text | default 'active' |
| `created_at` | timestamptz | default now() |

### `milestones`

Weekly milestones within a goal.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `goal_id` | uuid | FK → goals, ON DELETE CASCADE |
| `week_number` | integer | NOT NULL |
| `title` | text | NOT NULL |
| `status` | text | default 'pending' |
| `created_at` | timestamptz | default now() |

### `tasks`

Time-blocked actions linked to goals and optionally milestones.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | uuid | FK → users, ON DELETE CASCADE |
| `goal_id` | uuid | FK → goals, ON DELETE CASCADE |
| `milestone_id` | uuid | FK → milestones, ON DELETE CASCADE, **nullable** |
| `title` | text | NOT NULL |
| `start_time` | timestamptz | nullable |
| `end_time` | timestamptz | nullable |
| `state` | task_state | default 'scheduled' |
| `priority` | task_priority | default 'standard' |
| `trigger_type` | trigger_type | default 'time' |
| `is_recurring` | boolean | default false |
| `calendar_event_id` | varchar(255) | nullable, indexed |
| `created_at` | timestamptz | default now() |

### `conversations`

AI conversation history (Goal Planner). `goal_id` is nullable so a conversation can be created before the goal is confirmed.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | uuid | FK → users, ON DELETE CASCADE |
| `goal_id` | uuid | FK → goals, ON DELETE CASCADE, **nullable** |
| `messages` | jsonb | default '[]' |
| `status` | text | default 'open' |
| `created_at` | timestamptz | default now() |

### `demo_flags`

Per-user demo mode controls (one row per user).

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | uuid | PK, FK → users, ON DELETE CASCADE |
| `virtual_now` | timestamptz | nullable, simulated current time |
| `escalation_speed` | float | default 1.0 |

---

## Relationships

```
users
 ├── goals (1:N)
 │    ├── milestones (1:N)
 │    ├── tasks (1:N)
 │    └── conversations (1:N)
 ├── tasks (1:N)
 └── demo_flags (1:1)
```

Foreign keys use `ON DELETE CASCADE`.

---

## Indexes

- `idx_goals_user_id`
- `idx_milestones_goal_id`
- `idx_tasks_user_id`, `idx_tasks_goal_id`, `idx_tasks_milestone_id`, `idx_tasks_calendar_event_id`
- `idx_conversations_user_id`, `idx_conversations_goal_id`

Seed data for local development: [supabase/scripts/seed_test_data.sql](../supabase/scripts/seed_test_data.sql).

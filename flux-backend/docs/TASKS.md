# Flux Backend — Task List

> Derived from `../docs/flux-tsd.md` (v2.0). Each task is atomic and independently implementable.
> Reference section numbers (§) map back to the TSD.

---

## Legend
- `[ ]` — not started
- `[x]` — done
- `[~]` — in progress
- **Bold** = blocking / must-do before dependents

---

## 0. Project Scaffolding

- [x] **0.1** Create `flux-backend/` directory tree exactly matching §2 repo structure
- [x] **0.2** Create `pyproject.toml` with all dependencies listed in §17 (FastAPI, LangGraph, LiteLLM, etc.)
- [x] **0.3** Run `uv sync` to generate `uv.lock`
- [x] **0.4** Create `.env.example` with every variable from §4 (no real values, placeholder comments)
- [x] 0.5 Create `app/__init__.py` and all sub-package `__init__.py` files
- [x] 0.6 Create top-level `README.md` with local dev quickstart (docker compose up, env setup)

---

## 1. Configuration (`app/config.py`)

- [x] **1.1** Implement `Settings` class using `pydantic-settings` with `SettingsConfigDict(env_file=".env")` — all fields from §4
- [x] 1.2 Add all App, Supabase, OpenRouter, LangSmith, Sentry, Twilio, VAPID, Redis, Notification, Cost Control, and Business Logic fields
- [x] 1.3 Export a module-level `settings = Settings()` singleton

---

## 2. Database Migrations (`migrations/`)

- [x] **2.1** Write `001_initial_schema.sql` — `users`, `goals`, `tasks`, `conversations`, `messages`, `patterns`, `notification_log`, `dispatch_log` tables exactly per §5
- [x] **2.2** Write `002_indexes.sql` — all partial and composite indexes from §5 (notifier push/whatsapp/call partial indexes critical for poll performance)
- [x] **2.3** Write `003_materialized_views.sql` — `user_weekly_stats`, `missed_by_category`, `activity_heatmap` views with unique indexes
- [x] **2.4** Write `004_rls_policies.sql` — enable RLS on all 8 user-data tables; create policies per §5 Migration 004
- [x] **2.5** Write `005_triggers.sql` — `refresh_analytics_views` trigger (AFTER UPDATE OF status ON tasks) + `update_patterns_timestamp` trigger
- [ ] 2.6 Apply migrations to Supabase project (via dashboard SQL editor or `psql`) and verify all tables/indexes exist

---

## 3. Supabase Service (`app/services/supabase.py`)

- [x] **3.1** Initialize `asyncpg` connection pool using `settings.database_url` (direct port 5432, not PgBouncer)
- [x] 3.2 Expose `db.fetch()`, `db.fetchrow()`, `db.execute()`, `db.fetchval()` async helpers wrapping the pool
- [x] 3.3 Add startup/shutdown lifecycle hooks to open/close the pool (register with FastAPI `lifespan`)
- [x] 3.4 Add Supabase Python client init (anon key) for JWT validation use in `dependencies.py`

---

## 4. LLM Service (`app/services/llm.py`) — §8

- [x] **4.1** Configure LiteLLM: set `api_key`, `api_base` to OpenRouter, `num_retries=2`, `request_timeout=30`
- [x] **4.2** Configure `litellm.fallbacks` for all 3 model tiers (GPT-4o ↔ Claude Sonnet 4, GPT-4o-mini → Claude Haiku)
- [x] **4.3** Implement `async llm_call(model, system, messages, max_tokens, user_id)` — builds full messages list, calls `litellm.acompletion`, adds OpenRouter attribution headers, returns raw text
- [x] **4.4** Implement `update_token_usage(user_id, provider, tokens)` — atomic JSONB update on `users.monthly_token_usage`
- [x] **4.5** Implement `check_token_budget(user_id) -> "ok" | "soft_limit" | "hard_limit"` — compares total against `settings.monthly_token_soft_limit` / `hard_limit`
- [x] 4.6 Wire `update_token_usage` call into `llm_call` when `user_id` is present and `response.usage` is non-null

---

## 5. Agent State (`app/agents/state.py`) — §7

- [x] **5.1** Define `AgentState` TypedDict with all fields: `user_id`, `conversation_history`, `intent`, `user_profile`, `goal_draft`, `proposed_tasks`, `classifier_output`, `scheduler_output`, `pattern_output`, `approval_status`, `error`, `token_usage`
- [x] 5.2 Add `Annotated` reducer types on `classifier_output`, `scheduler_output`, `pattern_output` so LangGraph `Send()` fan-out results merge correctly without overwriting each other
- [x] 5.3 Add `correlation_id: Optional[str]` field for end-to-end trace correlation with structlog

---

## 6. Pydantic Agent Output Models (`app/models/agent_outputs.py`) — §6

- [x] **6.1** `OrchestratorOutput` — `intent` Literal, `payload`, `clarification_question`, `task_id`, `goal_id`
- [x] **6.2** `GoalPlannerOutput` — `goal_feasible_in_6_weeks`, `micro_goal_roadmap`, `proposed_tasks` (list of `ProposedTask`), `conflicts_detected`, `plan_summary`, `approval_status`
- [x] 6.3 `ProposedTask` — `title`, `description`, `scheduled_days`, `suggested_time`, `duration_minutes`, `recurrence_rule`, `week_range`
- [x] 6.4 `MicroGoal` — `title`, `description`, `pipeline_order`, `target_weeks`
- [x] 6.5 `ConflictDetected` — `existing_task_title`, `scheduled_at`, `message`
- [x] **6.6** `ClassifierOutput` — `tags: list[str]`
- [x] **6.7** `SchedulerOutput` — `slots: list[SlotResult]`, `conflicts`, `first_available_start`
- [x] 6.8 `SlotResult` — `task_title`, `scheduled_at`, `duration_minutes`, `conflict`
- [x] **6.9** `PatternObserverOutput` — `best_times`, `avoid_slots` (list of `AvoidSlot`), `category_performance`, `general_notes`
- [x] 6.10 `AvoidSlot` — `day`, `time_range`, `reason`, `confidence`
- [x] 6.11 `CategoryPerformance` — `category`, `completion_rate`

---

## 7. LLM Validation Wrapper (`app/services/llm.py`) — §7

- [x] **7.1** Implement `validated_llm_call(model, system_prompt, messages, output_model, max_retries=2)` — parse JSON, validate against Pydantic model, on failure re-prompt with error message, raise after `max_retries` exhausted

---

## 8. Agent Prompts (`app/agents/prompts/`) — §6

- [x] 8.1 Write `orchestrator.txt` — intent classification prompt with 5 intent types, rules, exact JSON schema
- [x] 8.2 Write `goal_planner.txt` — coach/behavioral scientist persona, 7 principles, context inputs, negotiation loop instructions
- [x] 8.3 Write `classifier.txt` — 14-tag taxonomy, no-invent rule, JSON-only output
- [x] 8.4 Write `scheduler.txt` — availability rules (sleep block, work soft-block, 15-min buffer, no double-book), local timezone handling
- [x] 8.5 Write `pattern_observer.txt` — 3-datapoint minimum, low-confidence flag, day/time specificity rules

---

## 9. Agent Nodes

### 9.1 Orchestrator (`app/agents/orchestrator.py`) — §6.1
- [x] **9.1.1** Load system prompt from `prompts/orchestrator.txt`
- [x] **9.1.2** Build messages with conversation history + user profile context
- [x] **9.1.3** Call `validated_llm_call` with `OrchestratorOutput`, `max_tokens=512`
- [x] **9.1.4** Check `users.onboarded`; if `false`, override intent to `"ONBOARDING"` before routing
- [x] 9.1.5 Check `check_token_budget`; if `"hard_limit"`, downgrade model to `gpt-4o-mini`

### 9.2 Goal Planner (`app/agents/goal_planner.py`) — §6.2
- [x] **9.2.1** Load prompt from `prompts/goal_planner.txt`
- [x] **9.2.2** Build context: merge `classifier_output` + `scheduler_output` + `pattern_output` from state
- [x] **9.2.3** Call `validated_llm_call` with `GoalPlannerOutput`, `max_tokens=4096`
- [x] **9.2.4** Detect if goal cannot be done in 6 weeks → populate `micro_goal_roadmap`; write all non-first micro-goals to `goals` table with `status='pipeline'`
- [x] **9.2.5** Return `plan_summary` + `proposed_tasks` as assistant message to user
- [x] 9.2.6 Loop until `approval_status == "approved"` (handled by LangGraph conditional edge)
- [x] 9.2.7 On approval: trigger `save_tasks` node
- [x] 9.2.8 If `check_token_budget` returns `"hard_limit"`, use `gpt-4o-mini` fallback

### 9.3 Classifier (`app/agents/classifier.py`) — §6.3
- [x] **9.3.1** Load prompt from `prompts/classifier.txt`
- [x] **9.3.2** Call `validated_llm_call` with `ClassifierOutput`, `max_tokens=128`
- [x] 9.3.3 Write `class_tags` back to goal row in DB

### 9.4 Scheduler (`app/agents/scheduler.py`) — §6.4
- [x] **9.4.1** Load prompt from `prompts/scheduler.txt`
- [x] **9.4.2** Query existing `pending`/`rescheduled` tasks for user over next 6 weeks
- [x] **9.4.3** Load `sleep_window` and `work_hours` from `user_profile`
- [x] **9.4.4** Build slot-finding context (existing tasks, blocked windows, Pattern Observer hints)
- [x] **9.4.5** Call `validated_llm_call` with `SchedulerOutput`, `max_tokens=1024`
- [x] 9.4.6 Convert all `suggested_time` values from user local time to UTC using `pendulum` before returning

### 9.5 Pattern Observer (`app/agents/pattern_observer.py`) — §6.5
- [x] **9.5.1** Load prompt from `prompts/pattern_observer.txt`
- [x] **9.5.2** Query task history (completions + misses with timestamps) for the user
- [x] **9.5.3** Call `validated_llm_call` with `PatternObserverOutput`, `max_tokens=1024`
- [x] **9.5.4** Implement miss signal handler: check ≥3 consecutive misses in same slot (±1 hour, same day of week, 3 consecutive weeks); create/update `patterns` row if threshold met
- [x] 9.5.5 Skip overwrite if `patterns.data.user_overridden = true`
- [x] 9.5.6 Cold-start: if user has <14 days of data, use `chronotype` from profile as baseline; set `confidence < 0.5` on all patterns

### 9.6 Onboarding (`app/agents/onboarding.py`) — §12
- [x] **9.6.1** Implement conversational onboarding subgraph / node (11 questions in order per §12)
- [x] **9.6.2** Track which questions have been answered via state; skip already-answered ones on resume
- [x] **9.6.3** On phone number collection: trigger OTP send via Twilio Verify (`POST /account/phone/verify/send`)
- [x] **9.6.4** On WhatsApp opt-in: set `whatsapp_opt_in_at = now()` in users table
- [x] **9.6.5** On completion: write full profile JSON to `users.profile`, set `users.onboarded = true`, set `users.timezone`
- [x] 9.6.6 Pre-seed `existing_commitments` as `tasks` rows in DB after onboarding
- [x] 9.6.7 After onboarding completes: re-route to Orchestrator for first goal/task

---

## 10. LangGraph Graph Assembly (`app/agents/graph.py`) — §7

- [x] **10.1** Register all nodes: `orchestrator`, `clarify`, `onboarding`, `goal_planner`, `classifier`, `scheduler`, `pattern_observer`, `task_handler`, `goal_modifier`, `save_tasks`
- [x] **10.2** Set entry point to `orchestrator`
- [x] **10.3** Add `route_from_orchestrator` conditional edge: `ONBOARDING`, `GOAL`, `NEW_TASK`, `RESCHEDULE_TASK`, `MODIFY_GOAL`, `CLARIFY`
- [x] **10.4** `clarify → orchestrator` loop-back edge
- [x] **10.5** `onboarding → orchestrator` edge (re-route after completion)
- [x] **10.6** Implement `fan_out_to_subagents` using `Send()` for true parallel execution of `classifier`, `scheduler`, `pattern_observer` from `goal_planner`
- [x] **10.7** `classifier → goal_planner`, `scheduler → goal_planner`, `pattern_observer → goal_planner` reconvergence edges
- [x] **10.8** `check_user_approval` conditional edge from `goal_planner`: `APPROVED → save_tasks`, `NEGOTIATING → goal_planner`, `ABANDONED → END`
- [x] **10.9** `save_tasks → END`, `task_handler → save_tasks`, `goal_modifier → save_tasks`
- [x] **10.10** Set up `AsyncPostgresSaver` checkpointer using `settings.database_url` (direct port 5432)
- [x] 10.11 Compile graph with checkpointer and expose as `compiled_graph`

---

## 11. Task Handler & Save Tasks Nodes

- [x] **11.1** Implement `task_handler` node — handles `NEW_TASK` intent: validate task details, call Scheduler for slot, present to user for confirm
- [x] **11.2** Implement `save_tasks` node — bulk insert confirmed task rows to DB using `rrule_expander` for recurring tasks; handle `shared_with_goal_ids`
- [x] 11.3 Implement `goal_modifier` node — handles `MODIFY_GOAL`: cancel future occurrences of affected tasks, generate replacement tasks, run conflict detection, present for approval, write updates

---

## 12. RRULE Expander (`app/services/rrule_expander.py`) — §5

- [x] **12.1** Implement `expand_rrule_to_tasks(base_task, rrule_string, start_dt, end_dt, user_timezone)` using `python-dateutil` `rrulestr`
- [x] 12.2 Convert each occurrence from user local time to UTC via `pendulum` before appending to output list
- [x] 12.3 Write unit test covering weekly recurrence across a DST boundary

---

## 13. Context Manager (`app/services/context_manager.py`) — §15

- [x] **13.1** Implement `window_conversation_history(history, user_id)` — check len and token count against config limits
- [x] **13.2** Split history at midpoint, summarize older half via `llm_call` with `gpt-4o-mini`, `max_tokens=500`
- [x] **13.3** Return `[summary_message] + recent` where `summary_message.role = "summary"`
- [x] 13.4 Write summary message to `messages` table with `role='summary'`

---

## 14. Notification Services

### 14.1 Push Service (`app/services/push_service.py`) — §9
- [x] **14.1.1** Implement `dispatch_push(task, user_push_subscription)` using `pywebpush`
- [x] 14.1.2 Build payload with `title`, `body`, `task_id`, and 3 action buttons (done / reschedule / missed)
- [x] 14.1.3 Use `settings.vapid_private_key` and `settings.vapid_claims_email`
- [x] 14.1.4 Catch `WebPushException` and log warning without re-raising (expired subscriptions are non-fatal)

### 14.2 Twilio Service (`app/services/twilio_service.py`) — §9
- [x] **14.2.1** Initialize Twilio `Client` with `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`
- [x] **14.2.2** Implement `dispatch_whatsapp(task) -> str` — gate on `phone_verified` and `whatsapp_opt_in_at`; check remaining-day slots for reschedule option; return `MessageSid`
- [x] **14.2.3** Implement `dispatch_call(task) -> str` — gate on `phone_verified`; build TwiML with `<Gather>` DTMF; build `callback_url` from `settings.twilio_webhook_base_url`; return `CallSid`
- [x] 14.2.4 Implement `send_otp(phone_number)` — Twilio Verify `verifications.create(to=phone, channel='sms')`
- [x] 14.2.5 Implement `confirm_otp(phone_number, code) -> bool` — Twilio Verify `verification_checks.create(to=phone, code=code)`; return `True` if `status == 'approved'`

---

## 15. Notifier Worker (`notifier/`)  — §6.6, §9

### 15.1 Entry Point (`notifier/main.py`)
- [x] **15.1.1** Set up `AsyncIOScheduler` with `SQLAlchemyJobStore` using `settings.database_url` (strip `+asyncpg` prefix for sync SQLAlchemy URL)
- [x] **15.1.2** On startup: call `recover_stuck_dispatches()` before starting scheduler
- [x] **15.1.3** Add `notification_poll` job with `interval` trigger, `seconds=settings.notification_poll_interval_seconds`
- [x] 15.1.4 Keep-alive using `asyncio.Event().wait()`

### 15.2 Poll Loop (`notifier/poll.py`)
- [x] **15.2.1** Implement `notification_poll()` — query `due_push` tasks (scheduled_at in next `reminder_lead_minutes`, `reminder_sent_at IS NULL`, `status='pending'`, `trigger_type='time'`)
- [x] **15.2.2** For each push task: atomic CAS `UPDATE tasks SET reminder_sent_at=now() WHERE id=$1 AND reminder_sent_at IS NULL RETURNING id`; only dispatch if `RETURNING` yields a row
- [x] **15.2.3** Query `due_whatsapp` tasks (push sent > `escalation_window` ago, `whatsapp_sent_at IS NULL`)
- [x] **15.2.4** For each whatsapp task: atomic CAS on `whatsapp_sent_at`; dispatch; store `MessageSid` in `notification_log.external_id`
- [x] **15.2.5** Query `due_call` tasks (whatsapp sent > `escalation_window` ago, `call_sent_at IS NULL`)
- [x] **15.2.6** For each call task: atomic CAS on `call_sent_at`; dispatch; store `CallSid` in `notification_log.external_id`
- [x] **15.2.7** Query `due_miss` tasks (call sent > `escalation_window` ago, `status='pending'`); set `status='missed'`; call `check_and_flag_pattern` async for Pattern Observer
- [x] 15.2.8 Implement `log_dispatch(task_id, channel)` — insert `dispatch_log` row with `status='pending'`
- [x] 15.2.9 Implement `mark_dispatch_done(task_id, channel, external_id=None)` — update `dispatch_log` to `status='dispatched'`, write to `notification_log`
- [x] 15.2.10 Implement `check_and_flag_pattern(user_id, task_id)` — call Pattern Observer miss signal handler if miss is 3rd consecutive in same slot

### 15.3 Recovery (`notifier/recovery.py`)
- [x] **15.3.1** Implement `recover_stuck_dispatches()` — query `dispatch_log WHERE status='pending' AND created_at < now()-5min`; re-attempt dispatch for each

---

## 16. Middleware

### 16.1 Auth (`app/middleware/auth.py`) — §11, §13
- [x] **16.1.1** Implement `get_current_user` FastAPI dependency using `HTTPBearer`
- [x] 16.1.2 Validate Supabase JWT via `supabase.auth.get_user(token)`; raise `HTTP 401` on failure
- [x] 16.1.3 Return user object with `user.id` accessible downstream

### 16.2 Structured Logging (`app/middleware/logging.py`) — §14
- [x] **16.2.1** Configure `structlog` with `TimeStamper`, `add_log_level`, `JSONRenderer` processors
- [x] **16.2.2** Implement `StructlogMiddleware(BaseHTTPMiddleware)` — generate `correlation_id` UUID per request; bind to structlog context; add `X-Correlation-ID` response header

### 16.3 Rate Limiting (`app/middleware/rate_limit.py`) — §16
- [x] **16.3.1** Configure `slowapi.Limiter` with per-user key function (`request.state.user.id`) and Redis storage
- [x] 16.3.2 Apply decorators to endpoints with limits per §16 table (chat: 20/min, analytics: 30/min, OTP send: 3/hr, etc.)

---

## 17. API Endpoints (`app/api/v1/`)

### 17.1 Chat (`chat.py`) — §11
- [x] **17.1.1** `POST /api/v1/chat/message` — validate body (`message`, `conversation_id`); create or resume conversation; invoke `compiled_graph` with `thread_id`; apply `window_conversation_history`; persist user + assistant messages to `messages` table; return response
- [x] **17.1.2** Support `conversation_id=null` — create new `conversations` row with fresh `langgraph_thread_id` (UUID)
- [x] 17.1.3 `GET /api/v1/chat/history` — query `messages` for given `conversation_id` with `limit` param; verify conversation belongs to authenticated user
- [x] 17.1.4 Apply `@limiter.limit("20/minute")` to `POST /chat/message`

### 17.2 Goals (`goals.py`) — §11
- [x] **17.2.1** `GET /api/v1/goals` — filter by `status` query param; return list with optional `pipeline` array for micro-goal chains
- [x] **17.2.2** `GET /api/v1/goals/{goal_id}` — single goal fetch; verify ownership via RLS / user_id check
- [x] 17.2.3 `PATCH /api/v1/goals/{goal_id}/abandon` — set `status='abandoned'`; cancel all future `pending` tasks not shared with other active goals
- [x] 17.2.4 `PATCH /api/v1/goals/{goal_id}/modify` — trigger `MODIFY_GOAL` intent through LangGraph with provided `message`
- [x] 17.2.5 `GET /api/v1/goals/{goal_id}/tasks` — return all tasks for goal

### 17.3 Tasks (`tasks.py`) — §11
- [x] **17.3.1** `GET /api/v1/tasks/today` — return all `pending` tasks for current day in user's local timezone, ordered by `scheduled_at`
- [x] 17.3.2 `GET /api/v1/tasks/{task_id}` — single task fetch
- [x] **17.3.3** `PATCH /api/v1/tasks/{task_id}/complete` — set `status='done'`, `completed_at=now()`; check if task was last in current sprint → activate next pipeline goal
- [x] **17.3.4** `PATCH /api/v1/tasks/{task_id}/missed` — set `status='missed'`; trigger Pattern Observer miss signal async
- [x] 17.3.5 `POST /api/v1/tasks/{task_id}/reschedule` — invoke Scheduler via LangGraph; return proposed `scheduled_at` for user confirmation

### 17.4 Analytics (`analytics.py`) — §10, §11
- [x] **17.4.1** `GET /api/v1/analytics/overview` — compute `streak_days` (streak SQL from §10), `today_completion_pct`, `today_done`, `today_total`; return `heatmap` from `activity_heatmap` view
- [x] 17.4.2 `GET /api/v1/analytics/goals` — per-goal progress bars from `tasks` table; category breakdown
- [x] 17.4.3 `GET /api/v1/analytics/missed-by-cat` — query `missed_by_category` view
- [x] 17.4.4 `GET /api/v1/analytics/weekly?weeks=N` — rolling N-week completion from `user_weekly_stats`; default N=12
- [x] 17.4.5 Apply `@limiter.limit("30/minute")` to all analytics endpoints

### 17.5 Patterns (`patterns.py`) — §11
- [x] **17.5.1** `GET /api/v1/patterns` — return all patterns for user ordered by `updated_at DESC`
- [x] 17.5.2 `GET /api/v1/patterns/{pattern_id}` — single pattern
- [x] **17.5.3** `PATCH /api/v1/patterns/{pattern_id}` — accept `user_override`, `description`, `confidence`; set `data.user_overridden=true` in JSONB; update `confidence` and `description`
- [x] 17.5.4 `DELETE /api/v1/patterns/{pattern_id}` — hard delete; return `HTTP 204`

### 17.6 Account (`account.py`) — §11
- [x] **17.6.1** `GET /api/v1/account/me` — return profile, notification preferences, monthly token usage summary
- [x] 17.6.2 `PATCH /api/v1/account/me` — update `notification_preferences` (reminder lead, escalation window)
- [x] **17.6.3** `POST /api/v1/account/phone/verify/send` — call `send_otp(phone_number)`; rate limit 3/hour
- [x] **17.6.4** `POST /api/v1/account/phone/verify/confirm` — call `confirm_otp`; on success set `phone_verified=true` in DB
- [x] **17.6.5** `POST /api/v1/account/whatsapp/opt-in` — gate on `phone_verified=true`; set `whatsapp_opt_in_at=now()`
- [x] 17.6.6 `DELETE /api/v1/account` — GDPR erasure: cascade-delete all user data rows (tasks, goals, patterns, messages, conversations, notification_log, dispatch_log), delete LangGraph checkpoint threads, delete `users` row, queue OpenRouter data deletion
- [x] 17.6.7 `GET /api/v1/account/export` — GDPR portability: collect all user data (profile, goals, tasks, messages, patterns); return as JSON ZIP

### 17.7 Webhooks (`webhooks.py`) — §11
- [x] **17.7.1** Implement Twilio signature validator (`twilio.request_validator.RequestValidator`); apply to both webhook routes; reject with `HTTP 403` on invalid signature
- [x] **17.7.2** `POST /api/v1/webhooks/twilio/whatsapp` — parse `Body` field; map `"1"`/`"done"` → complete, `"2"`/`"reschedule"` → generate deep link, `"3"`/`"missed"` → missed; use `MessageSid` as idempotency key on `notification_log.external_id`
- [x] **17.7.3** `POST /api/v1/webhooks/twilio/voice` — parse `Digits` DTMF; map `1/2/3` same as WhatsApp; use `CallSid` as idempotency key; accept `task_id` from query param

### 17.8 Demo (`demo.py`) — §11
- [x] 17.8.1 `POST /api/v1/demo/trigger-location` — query all `pending` tasks with `trigger_type='location'` for user; fire notification chain for each

---

## 18. FastAPI App Assembly (`app/main.py`) — §11

- [x] **18.1** Initialize Sentry before `FastAPI()` creation — `sentry_sdk.init(...)` with `FastApiIntegration`, `AsyncioIntegration`, `send_default_pii=False`
- [x] **18.2** Create `FastAPI` app with `title`, `version`, `docs_url`, `redoc_url`, `openapi_url`
- [x] **18.3** Register `slowapi` limiter and `RateLimitExceeded` exception handler
- [x] **18.4** Add `StructlogMiddleware` and `CORSMiddleware` (allow all origins for MVP)
- [x] **18.5** Include all 8 routers with `prefix="/api/v1"` and appropriate tags
- [x] 18.6 Implement `custom_openapi()` — add `BearerAuth` security scheme to generated schema
- [x] 18.7 Wire `lifespan` context manager for asyncpg pool startup/shutdown and LangGraph checkpointer init

---

## 19. API Request/Response Schemas (`app/models/api_schemas.py`) — §11

- [x] 19.1 `ChatMessageRequest` — `message: str`, `conversation_id: Optional[str]`
- [x] 19.2 `ChatMessageResponse` — `conversation_id`, `message`, `agent_node`, `proposed_plan`, `requires_user_action`
- [x] 19.3 `ChatHistoryResponse` — `messages: list[MessageSchema]` with `id`, `role`, `content`, `agent_node`, `created_at`
- [x] 19.4 `GoalResponse`, `GoalListResponse`
- [x] 19.5 `TaskResponse`, `TaskListResponse`
- [x] 19.6 `AnalyticsOverviewResponse`, `WeeklyStatsResponse`, `MissedByCatResponse`
- [x] 19.7 `PatternResponse`, `PatternPatchRequest`
- [x] 19.8 `AccountMeResponse`, `AccountPatchRequest`
- [x] 19.9 `PhoneVerifySendRequest`, `PhoneVerifyConfirmRequest`
- [x] 19.10 `RescheduleRequest` — `message: str`
- [x] 19.11 `GoalModifyRequest` — `message: str`

---

## 20. Docker & Deployment — §17

- [x] **20.1** Write `docker/Dockerfile.api` — python:3.12-slim, install uv, `uv sync --frozen --no-dev`, expose 8000, uvicorn with 4 workers
- [x] **20.2** Write `docker/Dockerfile.notifier` — same base, include `notifier/` dir, run `python -m notifier.main`
- [x] **20.3** Write `docker-compose.yml` — `api`, `notifier`, `redis` services; hot-reload volume mount for api in dev; `restart: unless-stopped` on notifier
- [x] 20.4 Write `docker-compose.prod.yml` — production overrides (no volume mounts, no --reload, health checks)
- [ ] 20.5 Verify `docker compose up` brings all services up cleanly with no import errors

---

## 21. Testing — §18

### 21.1 Unit Tests (`tests/unit/`)
- [x] **21.1.1** `test_orchestrator.py` — mock `llm_call`; assert intent classification for GOAL, NEW_TASK, CLARIFY, RESCHEDULE_TASK, MODIFY_GOAL
- [x] **21.1.2** `test_goal_planner.py` — mock `llm_call`; assert `GoalPlannerOutput` validation; test micro-goal decomposition path
- [x] 21.1.3 `test_classifier.py` — assert all 14 valid tags accepted; invalid tags raise `ValidationError`
- [x] 21.1.4 `test_scheduler.py` — assert UTC conversion; assert no double-booking logic
- [x] **21.1.5** `test_validated_llm_call.py` — assert retry on malformed JSON; assert `ValueError` after `max_retries` exhausted
- [x] **21.1.6** `test_rrule_expander.py` — test weekly recurrence; test DST boundary; test `end_dt` boundary exclusion
- [x] 21.1.7 `test_context_manager.py` — assert summarization triggers at message limit; assert summary is prepended correctly
- [x] 21.1.8 `test_token_budget.py` — assert `check_token_budget` returns correct status at soft/hard thresholds

### 21.2 Integration Tests (`tests/integration/`)
- [x] **21.2.1** `test_chat_endpoint.py` — POST /chat/message creates conversation, invokes graph, returns response
- [x] 21.2.2 `test_goal_flow.py` — end-to-end: submit goal → plan returned → approve → tasks written to DB
- [x] **21.2.3** `test_notification_idempotency.py` — simulate two concurrent workers claiming same task; assert only one dispatches (CAS test)
- [x] 21.2.4 `test_twilio_webhook.py` — assert invalid Twilio signature returns 403; assert valid signature processes correctly
- [x] 21.2.5 `test_gdpr_delete.py` — assert `DELETE /account` cascades all rows

### 21.3 Test Infrastructure (`tests/conftest.py`)
- [ ] **21.3.1** Set up async test DB fixtures using a separate test Supabase project or local Postgres
- [x] 21.3.2 Create `pytest-asyncio` `asyncio_mode = "auto"` config in `pytest.ini` or `pyproject.toml`
- [x] 21.3.3 Add `AsyncMock` helper fixtures for `llm_call` and Twilio client

---

## 22. Observability Setup — §14

- [ ] 22.1 Verify LangSmith traces appear at `smith.langchain.com` with `LANGCHAIN_TRACING_V2=true`
- [ ] 22.2 Configure Sentry alert rules: LLM error rate > 5%, dispatch failure > 5%, p95 latency > 10s, any Notifier unhandled exception
- [ ] 22.3 Verify `correlation_id` flows through LangGraph state and appears in all structlog output
- [ ] 22.4 Add `monthly_token_usage` reset cron job — monthly scheduled job to zero out `users.monthly_token_usage` and update `reset_at`

---

## 23. Security Hardening — §13

- [ ] **23.1** Verify RLS policies are active and service role key is used for all backend writes (never anon key for writes)
- [ ] **23.2** Confirm `send_default_pii=False` in Sentry init
- [ ] **23.3** Confirm only `user_id` UUIDs (never names/emails/phones) are passed in LLM prompt context
- [ ] 23.4 Confirm all WhatsApp dispatch is double-gated: `phone_verified=true` AND `whatsapp_opt_in_at IS NOT NULL`
- [ ] 23.5 Confirm Twilio webhook signature validation is applied and cannot be bypassed
- [ ] 23.6 Confirm `DATABASE_URL` uses direct connection (port 5432), not PgBouncer (port 6543)

---

## 24. Final Integration Checklist

- [ ] 24.1 End-to-end smoke test: new user → onboarding chat → goal creation → plan approved → tasks visible in DB → notification fired at scheduled time
- [ ] 24.2 Test WhatsApp sandbox flow with a real phone number (join sandbox keyword → receive message → reply "1" → task marked done)
- [ ] 24.3 Test DTMF voice call flow (trigger call → press 1 → task marked done via webhook)
- [ ] 24.4 Verify `/docs` Swagger UI loads and all endpoints are documented
- [ ] 24.5 Verify `docker compose up` (fresh) succeeds with only `.env` set
- [ ] 24.6 Deploy to Railway/Render staging; verify both API and Notifier services start and stay healthy
- [ ] 24.7 Verify `GET /api/v1/analytics/overview` returns correct streak and heatmap data after several tasks completed
- [ ] 24.8 Test GDPR export: `GET /account/export` returns zip with all user data
- [ ] 24.9 Test GDPR delete: `DELETE /account` leaves no orphan rows in any table

---

## Dependency Order (Critical Path)

```
0 (Scaffolding)
  → 1 (Config)
    → 3 (Supabase service)
      → 2 (Migrations — apply to DB)
    → 4 (LLM service)
      → 7 (validated_llm_call)
        → 5 (AgentState) + 6 (Pydantic models) + 8 (Prompts)
          → 9 (Agent nodes)
            → 10 (LangGraph graph)
              → 11 (task_handler / save_tasks / goal_modifier)
                → 12 (RRULE expander)
              → 13 (Context manager)
  → 14 (Notification services)
    → 15 (Notifier worker)
  → 16 (Middleware)
    → 17 (API endpoints — requires graph + services)
      → 18 (App assembly)
        → 19 (API schemas)
  → 20 (Docker)
  → 21 (Tests)
  → 22 (Observability)
  → 23 (Security hardening)
  → 24 (Final checklist)
```

---

*Last updated: 2026-02-26. Reflects TSD v2.0. All section references (§N) map to `docs/flux-tsd.md`.*

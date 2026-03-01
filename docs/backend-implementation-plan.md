# Flux Backend — Comprehensive Implementation Plan

> **Source of Truth:** [flux-tsd.md](flux-tsd.md) (Version 2.0 — Greenfield)
> **Target Directory:** `/backend` (project root)
> **Team:** 4 Backend Engineers
> **Stack:** Python 3.12 · FastAPI · LangGraph · Supabase · Twilio · LiteLLM · LangSmith · Sentry

---

## Table of Contents

1. [Implementation Philosophy](#implementation-philosophy)
2. [Phase 0 — Project Scaffolding & Tooling](#phase-0--project-scaffolding--tooling)
3. [Phase 1 — Core Infrastructure](#phase-1--core-infrastructure)
4. [Phase 2 — Database & Migrations](#phase-2--database--migrations)
5. [Phase 3 — Agent Framework](#phase-3--agent-framework)
6. [Phase 4 — API Layer](#phase-4--api-layer)
7. [Phase 5 — Notification Engine](#phase-5--notification-engine)
8. [Phase 6 — Observability & Operational Readiness](#phase-6--observability--operational-readiness)
9. [Phase 7 — Testing](#phase-7--testing)
10. [Phase 8 — Docker & Deployment](#phase-8--docker--deployment)
11. [Phase 9 — Documentation & Agent Context](#phase-9--documentation--agent-context)
12. [Phase 10 — Setup & Initialization Scripts](#phase-10--setup--initialization-scripts)
13. [Open Questions & Gaps](#open-questions--gaps)

---

## Implementation Philosophy

Each phase is designed to be **independently testable** — you should be able to verify each phase before moving on. Dependencies flow downward (Phase N depends on Phase N-1). Within each phase, tasks are listed in dependency order.

> [!IMPORTANT]
> All code lives under `/backend` at the project root. The existing `/old-backend` is **not** being modified or migrated — this is a **greenfield build** per TSD v2.0.

---

## Phase 0 — Project Scaffolding & Tooling

**Goal:** Establish the project skeleton, package manager, and dependency tree so every subsequent phase has a working import base.

### Step 0.1 — Initialize `uv` project

```bash
cd backend/
uv init --name flux-backend --python 3.12
```

- Create `pyproject.toml` with all dependencies listed in TSD §17 (pyproject.toml section)
- Pin Python `>=3.12`
- Include `[project.optional-dependencies] dev` for test tooling

### Step 0.2 — Create directory structure

Create the full directory tree exactly as defined in TSD §2:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       ├── goals.py
│   │       ├── tasks.py
│   │       ├── analytics.py
│   │       ├── patterns.py
│   │       ├── account.py
│   │       ├── demo.py
│   │       └── webhooks.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── orchestrator.py
│   │   ├── goal_planner.py
│   │   ├── classifier.py
│   │   ├── scheduler.py
│   │   ├── pattern_observer.py
│   │   ├── onboarding.py
│   │   └── prompts/
│   │       ├── orchestrator.txt
│   │       ├── goal_planner.txt
│   │       ├── classifier.txt
│   │       ├── scheduler.txt
│   │       └── pattern_observer.txt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent_outputs.py
│   │   ├── api_schemas.py
│   │   └── db_schemas.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── supabase.py
│   │   ├── llm.py
│   │   ├── twilio_service.py
│   │   ├── push_service.py
│   │   ├── rrule_expander.py
│   │   ├── context_manager.py
│   │   └── analytics_service.py
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py
│       ├── rate_limit.py
│       └── logging.py
├── notifier/
│   ├── __init__.py
│   ├── main.py
│   ├── poll.py
│   ├── dispatch.py
│   └── recovery.py
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_indexes.sql
│   ├── 003_materialized_views.sql
│   ├── 004_rls_policies.sql
│   └── 005_triggers.sql
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── __init__.py
│   └── integration/
│       └── __init__.py
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.notifier
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── AGENTS.md
```

### Step 0.3 — Create `.env.example`

Populate with all environment variables from TSD §4, with placeholder values and descriptive comments.

### Step 0.4 — Create `.gitignore`

Standard Python + uv gitignore:
- `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `uv.lock` (or include lock per team preference), `dist/`, `.pytest_cache/`, `.coverage`

### Step 0.5 — Install dependencies

```bash
uv sync
```

Verify all packages resolve and install cleanly.

### ✅ Phase 0 Verification
- [ ] `uv sync` completes without errors
- [ ] All directories and `__init__.py` files exist
- [ ] `python -c "import fastapi, langgraph, litellm, sentry_sdk"` succeeds inside the venv

---

## Phase 1 — Core Infrastructure

**Goal:** Set up the configuration layer, database client, LLM wrapper, and Supabase integration so all downstream code can import and use them.

### Step 1.1 — Settings (`app/config.py`)

Implement the `Settings` class using `pydantic-settings` exactly as shown in TSD §4. This is the centralized config — every other module imports `settings` from here.

### Step 1.2 — Supabase Client (`app/services/supabase.py`)

- Initialize async connection pool using `asyncpg` and `DATABASE_URL`
- Create helper methods: `fetch()`, `fetchrow()`, `execute()`, `fetch_val()`
- Initialize `supabase-py` client for auth JWT validation (using `SUPABASE_URL` + `SUPABASE_ANON_KEY`)
- Service-role client for server-side writes (using `SUPABASE_SERVICE_ROLE_KEY`)

### Step 1.3 — LLM Wrapper (`app/services/llm.py`)

Implement per TSD §8:
- Configure LiteLLM with OpenRouter settings (`api_key`, `api_base`)
- Set fallback chains per TSD §8 (LiteLLM `fallbacks` config)
- Implement `llm_call()` function with token tracking
- Implement `validated_llm_call()` with Pydantic retry loop (TSD §7)
- Implement `update_token_usage()` and `check_token_budget()` per TSD §8

### Step 1.4 — Auth Dependency (`app/dependencies.py`)

Implement `get_current_user()` dependency that validates Supabase JWTs per TSD §11.

### Step 1.5 — Structured Logging Middleware (`app/middleware/logging.py`)

Implement `StructlogMiddleware` per TSD §14 — JSON-formatted logs with correlation IDs.

### Step 1.6 — Rate Limiting Middleware (`app/middleware/rate_limit.py`)

Set up `slowapi` with Redis backend per TSD §16. Define per-endpoint limits.

> [!NOTE]
> Rate limiting is **disabled** when `APP_ENV=development`. The middleware should check `settings.app_env` and skip enforcement in development mode. Redis is still provisioned locally for APScheduler's job store.

### ✅ Phase 1 Verification
- [ ] `Settings` loads from a `.env` file (or fails with clear validation errors for missing required vars)
- [ ] Supabase async pool connects to the database
- [ ] `llm_call()` can be invoked (test with a simple prompt to OpenRouter)
- [ ] Auth dependency raises `HTTP 401` on invalid tokens
- [ ] Structlog middleware emits JSON logs with correlation IDs

---

## Phase 2 — Database & Migrations

**Goal:** Create all SQL migrations and apply them to Supabase.

### Step 2.1 — Migration 001: Initial Schema

Create `migrations/001_initial_schema.sql` with all 8 tables per TSD §5:
- `users`, `goals`, `tasks`, `conversations`, `messages`, `patterns`, `notification_log`, `dispatch_log`

> [!NOTE]
> The `conversations` table must be created **before** `messages` due to the FK dependency. This is already corrected in the TSD.

### Step 2.2 — Migration 002: Indexes

Create `migrations/002_indexes.sql` per TSD §5 (all 12 indexes, including partial indexes for the notifier).

### Step 2.3 — Migration 003: Materialized Views

Create `migrations/003_materialized_views.sql` per TSD §5:
- `user_weekly_stats`, `missed_by_category`, `activity_heatmap`
- Each with a unique index for `REFRESH MATERIALIZED VIEW CONCURRENTLY`

### Step 2.4 — Migration 004: RLS Policies

Create `migrations/004_rls_policies.sql` per TSD §5. Enable RLS on all user-data tables, create owner-based policies.

### Step 2.5 — Migration 005: Triggers

Create `migrations/005_triggers.sql` per TSD §5:
- Analytics view refresh trigger (on task status update)
- Patterns `updated_at` auto-update trigger

### Step 2.6 — Pydantic DB Schemas (`app/models/db_schemas.py`)

Create Pydantic models that mirror the SQL tables for internal use (not ORM — raw SQL with typed responses).

### ✅ Phase 2 Verification
- [ ] All 5 migration files exist and are valid SQL
- [ ] Migrations apply successfully against a fresh Supabase project (in order: 001 → 005)
- [ ] RLS policies work: direct Supabase client with anon key can only read own data
- [ ] Materialized views return data after inserting test rows

---

## Phase 3 — Agent Framework

**Goal:** Implement all 6 agents and the LangGraph orchestration graph.

### Step 3.1 — Agent State (`app/agents/state.py`)

Define `AgentState` TypedDict per TSD §7.

### Step 3.2 — Pydantic Agent Output Models (`app/models/agent_outputs.py`)

Define all Pydantic models per TSD §6:
- `OrchestratorOutput` (§6.1)
- `GoalPlannerOutput`, `ProposedTask`, `MicroGoal`, `ConflictDetected` (§6.2)
- `ClassifierOutput` (§6.3)
- `SchedulerOutput`, `SlotResult` (§6.4)
- `PatternObserverOutput`, `AvoidSlot`, `CategoryPerformance` (§6.5)

### Step 3.3 — System Prompts (`app/agents/prompts/`)

Create all 5 `.txt` prompt files with exact content from TSD §6:
- `orchestrator.txt`, `goal_planner.txt`, `classifier.txt`, `scheduler.txt`, `pattern_observer.txt`

### Step 3.4 — Agent Node Implementations

Implement each agent as a LangGraph-compatible async node function:

| File | Agent | TSD Section | Notes |
|------|-------|-------------|-------|
| `orchestrator.py` | Orchestrator | §6.1 | Intent classification, routing |
| `goal_planner.py` | Goal Planner | §6.2 | Multi-turn negotiation, micro-goal decomposition |
| `classifier.py` | Classifier | §6.3 | 1–3 tags from fixed taxonomy |
| `scheduler.py` | Scheduler | §6.4 | Slot-finding, conflict detection, RRULE expansion |
| `pattern_observer.py` | Pattern Observer | §6.5 | Behavioral analysis, cold-start strategy |
| `onboarding.py` | Onboarding | §12 | Conversational profile building |

Each node must:
1. Load the system prompt from `prompts/`
2. Call `validated_llm_call()` with the correct model string (per TSD §3 model assignments)
3. Return the validated Pydantic model result
4. Handle errors gracefully

### Step 3.5 — RRULE Expander Service (`app/services/rrule_expander.py`)

Implement per TSD §5 (RRULE Expansion Strategy). Used by the Scheduler to materialize recurring task rows.

### Step 3.6 — Context Manager Service (`app/services/context_manager.py`)

Implement `window_conversation_history()` per TSD §15 — sliding window with GPT-4o-mini summarization when history exceeds limits.

### Step 3.7 — LangGraph Graph Assembly (`app/agents/graph.py`)

Wire the full graph per TSD §7:
- Entry point: `orchestrator`
- Conditional routing from orchestrator → 6 destinations
- `Send()` fan-out from `goal_planner` → `classifier`, `scheduler`, `pattern_observer` (parallel)
- Sub-agent reconvergence back to `goal_planner`
- Approval check conditional edges → `save_tasks` / negotiation loop / END
- `AsyncPostgresSaver` checkpointer via Supabase direct connection
- Helper nodes: `clarify_node`, `task_handler_node`, `goal_modifier_node`, `save_tasks_node`

### ✅ Phase 3 Verification
- [ ] Each agent node can be tested in isolation with mocked `llm_call`
- [ ] Pydantic models validate against sample LLM output
- [ ] LangGraph graph compiles without errors (`graph.compile()`)
- [ ] `Send()` fan-out produces parallel execution (test with timing assertions)
- [ ] `rrule_expander` correctly generates individual task dicts from sample RRULE strings
- [ ] Context manager produces windowed history under message/token limits

---

## Phase 4 — API Layer

**Goal:** Implement all HTTP route handlers as defined in TSD §11.

### Step 4.1 — API Schemas (`app/models/api_schemas.py`)

Define request/response Pydantic models for all endpoints:
- `ChatMessageRequest`, `ChatMessageResponse`
- `GoalResponse`, `GoalModifyRequest`
- `TaskResponse`, `RescheduleRequest`
- `AnalyticsOverviewResponse`, `WeeklyStatsResponse`
- `PatternResponse`, `PatternUpdateRequest`
- `AccountResponse`, `PhoneVerifyRequest`, `PhoneConfirmRequest`

### Step 4.2 — Chat Endpoints (`app/api/v1/chat.py`)

- `POST /api/v1/chat/message` — route through LangGraph, return `StreamingResponse`
- `GET /api/v1/chat/history` — paginated message retrieval
- Rate limit: 20 req/min per user

### Step 4.3 — Goal Endpoints (`app/api/v1/goals.py`)

- `GET /api/v1/goals` — filtered by status
- `GET /api/v1/goals/{goal_id}` — with pipeline micro-goals
- `PATCH /api/v1/goals/{goal_id}/abandon` — cascade cancel pending tasks
- `PATCH /api/v1/goals/{goal_id}/modify` — trigger MODIFY_GOAL intent
- `GET /api/v1/goals/{goal_id}/tasks`

### Step 4.4 — Task Endpoints (`app/api/v1/tasks.py`)

- `GET /api/v1/tasks/today` — today's pending tasks in user's timezone
- `GET /api/v1/tasks/{task_id}`
- `PATCH /api/v1/tasks/{task_id}/complete` — with micro-goal pipeline check
- `PATCH /api/v1/tasks/{task_id}/missed` — trigger pattern observer
- `POST /api/v1/tasks/{task_id}/reschedule`

### Step 4.5 — Analytics Endpoints (`app/api/v1/analytics.py`)

- `GET /api/v1/analytics/overview` — streak, today's stats, heatmap
- `GET /api/v1/analytics/goals` — per-goal progress
- `GET /api/v1/analytics/missed-by-cat` — grouped by category
- `GET /api/v1/analytics/weekly?weeks=12` — rolling weekly stats

### Step 4.6 — Pattern Endpoints (`app/api/v1/patterns.py`)

- `GET /api/v1/patterns`
- `GET /api/v1/patterns/{pattern_id}`
- `PATCH /api/v1/patterns/{pattern_id}` — user override
- `DELETE /api/v1/patterns/{pattern_id}` — hard delete (HTTP 204)

### Step 4.7 — Account Endpoints (`app/api/v1/account.py`)

- `GET /api/v1/account/me`
- `PATCH /api/v1/account/me`
- `POST /api/v1/account/phone/verify/send` — Twilio Verify OTP
- `POST /api/v1/account/phone/verify/confirm`
- `POST /api/v1/account/whatsapp/opt-in`
- `DELETE /api/v1/account` — GDPR cascading deletion
- `GET /api/v1/account/export` — GDPR data portability (JSON ZIP)

### Step 4.8 — Webhook Endpoints (`app/api/v1/webhooks.py`)

- `POST /api/v1/webhooks/twilio/whatsapp` — WhatsApp reply handler
- `POST /api/v1/webhooks/twilio/voice` — DTMF response handler
- **No JWT auth** — Twilio signature validation instead

### Step 4.9 — Demo Endpoints (`app/api/v1/demo.py`)

- `POST /api/v1/demo/trigger-location` — simulate location-based trigger

### Step 4.10 — FastAPI App Assembly (`app/main.py`)

- Sentry initialization
- Rate limiter setup
- CORS middleware
- Structlog middleware
- Router registration (all 8 routers)
- Custom OpenAPI schema per TSD §11

### ✅ Phase 4 Verification
- [ ] `uvicorn app.main:app --reload` starts without import errors
- [ ] Swagger UI at `/docs` lists all endpoints
- [ ] Each endpoint returns correct HTTP status codes for success and error cases
- [ ] Rate limiting is disabled in development mode
- [ ] CORS headers are present in responses

### Step 4.11 — Frontend Integration

Update the existing `/frontend` to integrate with the real backend:
1. Add an environment variable `VITE_API_BASE_URL=http://localhost:8000` to the frontend
2. Conditionally disable MSW (Mock Service Worker) when `VITE_API_BASE_URL` is set — MSW should only activate when no real backend is available
3. Configure CORS in the backend to allow the frontend's origin (`http://localhost:3000` or whatever port Vite uses)
4. Verify all frontend API calls (chat, goals, tasks) route to the real backend endpoints
5. Update `frontend/AGENTS.md` to document the backend integration

---

## Phase 5 — Notification Engine

**Goal:** Implement the Notifier worker as a separate process/container.

### Step 5.1 — Twilio Service (`app/services/twilio_service.py`)

- WhatsApp message dispatch
- Voice call dispatch with TwiML generation
- Twilio Verify OTP send/confirm

### Step 5.2 — Push Service (`app/services/push_service.py`)

- Web Push dispatch via `pywebpush` + VAPID keys per TSD §9

### Step 5.3 — Notification Poll Loop (`notifier/poll.py`)

Implement the full 4-stage escalation chain per TSD §6.6:
1. Push notification (at `T - reminder_lead_minutes`)
2. WhatsApp (after `escalation_window_minutes` with no response)
3. Voice call (after another `escalation_window_minutes`)
4. Auto-miss (after another `escalation_window_minutes`)

Each stage uses **atomic CAS** (`UPDATE ... WHERE ... IS NULL RETURNING id`) to prevent double-fire.

### Step 5.4 — Dispatch Layer (`notifier/dispatch.py`)

- `dispatch_push()`, `dispatch_whatsapp()`, `dispatch_call()`
- Idempotency via `notification_log.external_id` (Twilio MessageSid/CallSid)
- Reschedule deep link generation (check remaining day slots)

### Step 5.5 — Startup Recovery (`notifier/recovery.py`)

- On worker startup, recover stuck `dispatch_log` records (status='pending', created > 5min ago)

### Step 5.6 — Notifier Entry Point (`notifier/main.py`)

- APScheduler with SQLAlchemy PostgreSQL job store
- Polling interval from `NOTIFICATION_POLL_INTERVAL_SECONDS`

### Step 5.7 — Analytics Service (`app/services/analytics_service.py`)

- Streak calculation query
- Helper methods for materialized view queries

### ✅ Phase 5 Verification
- [ ] Notifier worker starts and polls without errors
- [ ] Push notification dispatches to a test subscription
- [ ] WhatsApp sends via Twilio sandbox
- [ ] Voice call initiates and DTMF callback works
- [ ] CAS prevents double-dispatch when two workers run simultaneously
- [ ] Recovery re-attempts stuck dispatches on restart

---

## Phase 6 — Observability & Operational Readiness

**Goal:** Wire up full observability stack.

### Step 6.1 — LangSmith Integration

- Verify `LANGCHAIN_TRACING_V2=true` enables automatic trace capture
- No code changes needed — just env var confirmation
- Verify traces appear at `https://smith.langchain.com/projects/flux-development`

### Step 6.2 — Sentry Integration

- Verify Sentry captures unhandled exceptions in both API and Notifier
- Confirm `send_default_pii=False` (GDPR)
- Set up Sentry alert rules per TSD §14

### Step 6.3 — Cost Control Enforcement

- Monthly token budget in `check_token_budget()` — soft warn + hard degrade
- Model downgrade at hard limit (Orchestrator/Goal Planner → GPT-4o-mini)
- Monthly reset cron job for `monthly_token_usage`

### ✅ Phase 6 Verification
- [ ] LangSmith traces appear for test agent calls
- [ ] Sentry captures test exceptions
- [ ] Token budget enforcement triggers model downgrade correctly

---

## Phase 7 — Testing

**Goal:** Comprehensive test suite covering all critical paths.

### Step 7.1 — Test Configuration (`tests/conftest.py`)

- Shared pytest fixtures: mock `llm_call`, test Supabase client, test user
- `pytest-asyncio` configuration

### Step 7.2 — Unit Tests (`tests/unit/`)

| Test File | Covers | Notes |
|-----------|--------|-------|
| `test_orchestrator.py` | Orchestrator intent classification | Mock LLM, test all 5 intents |
| `test_classifier.py` | Classifier tagging | Mock LLM, verify 1-3 tags from taxonomy |
| `test_scheduler.py` | Scheduler slot-finding | Mock existing tasks, verify no conflicts |
| `test_goal_planner.py` | Goal Planner plan generation | Mock all sub-agents, verify output structure |
| `test_pattern_observer.py` | Pattern detection | Mock task history, verify pattern extraction |
| `test_rrule_expander.py` | RRULE expansion | Test various RRULE strings, timezone handling |
| `test_context_manager.py` | Context windowing | Test summarization trigger at limits |
| `test_llm.py` | LLM retry + validation | Test retry loop on malformed JSON |
| `test_config.py` | Settings validation | Test missing required vars raise errors |

### Step 7.3 — Integration Tests (`tests/integration/`)

| Test File | Covers |
|-----------|--------|
| `test_chat_flow.py` | Full chat → agent → DB write flow |
| `test_notification_idempotency.py` | CAS double-fire prevention |
| `test_goal_lifecycle.py` | Goal creation → task generation → completion → pipeline advance |
| `test_gdpr_deletion.py` | Account deletion cascades correctly |

### ✅ Phase 7 Verification
- [ ] `uv run pytest tests/unit -v` — all unit tests pass
- [ ] `uv run pytest tests/integration -v` — all integration tests pass (requires test Supabase)
- [ ] Test coverage report generated with `pytest --cov=app --cov=notifier`

---

## Phase 8 — Docker & Deployment

**Goal:** Containerize the API and Notifier for local development and production.

### Step 8.1 — Dockerfile.api (`docker/Dockerfile.api`)

Per TSD §17. Python 3.12-slim base, uv for installs, `uvicorn` with 4 workers for production.

### Step 8.2 — Dockerfile.notifier (`docker/Dockerfile.notifier`)

Per TSD §17. Same base, but runs `python -m notifier.main`.

### Step 8.3 — docker-compose.yml (Local Dev)

Per TSD §17:
- `api` service (port 8000, hot reload via volume mount)
- `notifier` service (restart: unless-stopped)
- `redis` service (Redis 7 Alpine, port 6379)

### Step 8.4 — docker-compose.prod.yml

Production overrides:
- No volume mounts
- 4 `uvicorn` workers
- `restart: always` for notifier

### ✅ Phase 8 Verification
- [ ] `docker compose up --build` starts all 3 services
- [ ] API responds at `http://localhost:8000/docs`
- [ ] Notifier logs show polling activity
- [ ] Redis is reachable from API and Notifier containers

---

## Phase 9 — Documentation & Agent Context

**Goal:** Create all documentation that provides complete project context for AI agents and human contributors.

### Step 9.1 — `backend/README.md`

Comprehensive README covering:
- Project overview and architecture summary
- Tech stack with version pins
- Prerequisites (Python 3.12, uv, Docker, Supabase account)
- Quick start guide (clone → `.env` → `uv sync` → `docker compose up`)
- API documentation link (`/docs`)
- Development workflow (branching, testing, linting)
- Environment variable reference (link to `.env.example`)
- Deployment instructions (Railway/Render)
- Links to TSD and other docs

### Step 9.2 — `backend/AGENTS.md`

AI agent context document (for Claude Code, Cursor, Windsurf, etc.):
- **Project Context:** What Flux is, high-level architecture
- **Directory Map:** Purpose of each top-level directory and key files
- **Key Abstractions:**
  - How agents work (LangGraph nodes, Pydantic validation, prompt files)
  - How notifications work (escalation chain, CAS pattern)
  - How the DB is accessed (raw SQL via asyncpg, no ORM)
- **Coding Conventions:**
  - All LLM calls go through `app/services/llm.py`
  - All DB access goes through `app/services/supabase.py`
  - All environment config through `app/config.py`
  - Pydantic models for every agent output
  - System prompts stored as `.txt` files in `app/agents/prompts/`
  - All times stored in UTC, user timezone in `users.timezone`
- **Testing Patterns:**
  - How to mock LLM calls
  - How to write agent tests
  - How to run tests (`uv run pytest`)
- **Common Pitfalls:**
  - Must use Supabase **direct** connection (port 5432), not PgBouncer (6543)
  - Never use LLM model aliases — always pin exact version strings
  - CAS pattern is mandatory for notification dispatch
  - `send_default_pii=False` for Sentry (GDPR)

### Step 9.3 — `backend/API_REFERENCE.md`

Quick API reference summarizing all endpoints, request/response schemas, and rate limits. (Supplements the auto-generated Swagger at `/docs`.)

### Step 9.4 — `backend/ARCHITECTURE.md`

Architecture document with:
- System diagram (API server ↔ Supabase ↔ Notifier ↔ Twilio ↔ OpenRouter)
- LangGraph data flow diagram (Orchestrator → Agent nodes → DB)
- Notification escalation flow diagram
- Database ER diagram description

### Step 9.5 — `backend/CONTRIBUTING.md`

Contributor guide:
- How to set up the development environment
- How to run tests
- Code style guidelines
- PR review process
- How to add a new agent
- How to add a new API endpoint

### ✅ Phase 9 Verification
- [ ] All documentation files exist and are well-formatted
- [ ] `AGENTS.md` provides sufficient context for an AI agent to navigate and modify the codebase
- [ ] `README.md` quick start guide works from a fresh clone

---

## Phase 10 — Setup & Initialization Scripts

**Goal:** Create scripts that automate environment setup for new contributors.

### Step 10.1 — `scripts/setup.sh` (Main Setup Script)

Master setup script that:
1. Checks prerequisites (Python 3.12, uv, Docker, Docker Compose)
2. Creates `.env` from `.env.example` if not present
3. Prompts for required secrets (Supabase URL, keys, OpenRouter key, etc.)
4. Runs `uv sync` to install Python dependencies
5. Starts Docker Compose services (Redis)
6. Runs database migrations against Supabase
7. Prints success message with next steps

```bash
#!/usr/bin/env bash
# Usage: ./scripts/setup.sh
```

### Step 10.2 — `scripts/setup_supabase.sh`

Supabase-specific setup (defaults to **local mode**):
1. Checks for `supabase` CLI (install via `brew install supabase/tap/supabase` if missing)
2. Runs `supabase start` to spin up local Supabase (Postgres, Auth, REST API, Studio)
3. Captures the local `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` from `supabase status` output
4. Writes local credentials to `.env` (or displays them for manual copy)
5. Applies all migrations in order (001 through 005) via `supabase db push` or `psql`
6. Verifies tables, indexes, views, and RLS policies
7. Seeds test data (optional flag: `--seed`)
8. Supports `--cloud` flag to connect to a hosted Supabase project instead

### Step 10.3 — `scripts/run_migrations.sh`

Standalone migration runner:
1. Accepts `DATABASE_URL` from `.env` or CLI argument
2. Applies all SQL migration files in `migrations/` in order
3. Reports success/failure for each migration
4. Supports `--dry-run` flag for preview

### Step 10.4 — `scripts/generate_vapid_keys.sh`

VAPID key generation for Web Push:
1. Generates VAPID key pair using `openssl` or Python
2. Outputs base64-encoded keys
3. Optionally writes to `.env`

### Step 10.5 — `scripts/dev.sh` (Development Runner)

Development convenience script:
1. Starts Redis via Docker Compose
2. Runs API server with hot reload (`uvicorn ... --reload`)
3. Optionally starts Notifier worker in background
4. Provides clean shutdown (trap SIGINT)

### Step 10.6 — `scripts/test.sh`

Test runner:
1. Runs all unit tests: `uv run pytest tests/unit -v`
2. Optionally runs integration tests: `--integration`
3. Generates coverage report: `--coverage`
4. Exits with appropriate status code

### ✅ Phase 10 Verification
- [ ] `./scripts/setup.sh` runs on a fresh clone (macOS + Linux)
- [ ] `./scripts/dev.sh` starts the full dev stack
- [ ] `./scripts/test.sh` runs tests and produces output
- [ ] `./scripts/run_migrations.sh` applies migrations idempotently
- [ ] All scripts have `chmod +x` and proper shebangs

---

## Resolved Decisions

The following items were identified during TSD analysis. All have been resolved:

| # | Decision | Resolution |
|---|----------|------------|
| 1 | **Supabase Local vs. Cloud** | Use **Supabase CLI** (`supabase start`) for fully local development. Setup scripts support both local and cloud modes. |
| 2 | **`conversations` before `messages` (FK bug)** | **Fixed in TSD** — `conversations` table now defined before `messages` in Migration 001 (TSD §5). |
| 3 | **Rate limiting in development** | **Disabled** in local dev (`APP_ENV=development`). Redis is still used by APScheduler. Rate limiting only active when `APP_ENV=production`. |
| 4 | **WhatsApp API** | **Sandbox only** for MVP. No Meta Business API approval needed. TSD §13 updated to reflect this. |
| 5 | **OpenRouter access** | ✅ Confirmed — team has OpenRouter account with access to GPT-4o, Claude Sonnet 4, GPT-4o-mini. |
| 6 | **Frontend ↔ Backend integration** | Added as **Step 4.11** — update frontend to point to real backend, conditionally disable MSW, configure CORS. |
| 7 | **Data migration from `old-backend`** | **No migration.** The `/old-backend` folder is completely ignored. This is a greenfield build. |
| 8 | **LangGraph `Send()` reconvergence** | **Noted in TSD §7** — added implementation note about using `Annotated` types with custom reducers for state merging. |

> [!IMPORTANT]
> The `/old-backend` directory exists in the repo but is **not** referenced, migrated from, or used in any way. All backend code is built from scratch under `/backend`.

---

## Summary Task Checklist

```
Phase 0: Project Scaffolding
  [ ] 0.1 — Initialize uv project
  [ ] 0.2 — Create directory structure
  [ ] 0.3 — Create .env.example
  [ ] 0.4 — Create .gitignore
  [ ] 0.5 — Install dependencies

Phase 1: Core Infrastructure
  [ ] 1.1 — Settings (config.py)
  [ ] 1.2 — Supabase client
  [ ] 1.3 — LLM wrapper
  [ ] 1.4 — Auth dependency
  [ ] 1.5 — Structured logging middleware
  [ ] 1.6 — Rate limiting middleware

Phase 2: Database & Migrations
  [ ] 2.1 — Migration 001: Initial Schema
  [ ] 2.2 — Migration 002: Indexes
  [ ] 2.3 — Migration 003: Materialized Views
  [ ] 2.4 — Migration 004: RLS Policies
  [ ] 2.5 — Migration 005: Triggers
  [ ] 2.6 — Pydantic DB schemas

Phase 3: Agent Framework
  [ ] 3.1 — Agent state
  [ ] 3.2 — Pydantic agent output models
  [ ] 3.3 — System prompts
  [ ] 3.4 — Agent node implementations (6 agents)
  [ ] 3.5 — RRULE expander service
  [ ] 3.6 — Context manager service
  [ ] 3.7 — LangGraph graph assembly

Phase 4: API Layer
  [ ] 4.1 — API schemas
  [ ] 4.2 — Chat endpoints
  [ ] 4.3 — Goal endpoints
  [ ] 4.4 — Task endpoints
  [ ] 4.5 — Analytics endpoints
  [ ] 4.6 — Pattern endpoints
  [ ] 4.7 — Account endpoints
  [ ] 4.8 — Webhook endpoints
  [ ] 4.9 — Demo endpoints
  [ ] 4.10 — FastAPI app assembly
  [ ] 4.11 — Frontend integration

Phase 5: Notification Engine
  [ ] 5.1 — Twilio service
  [ ] 5.2 — Push service
  [ ] 5.3 — Notification poll loop
  [ ] 5.4 — Dispatch layer
  [ ] 5.5 — Startup recovery
  [ ] 5.6 — Notifier entry point
  [ ] 5.7 — Analytics service

Phase 6: Observability
  [ ] 6.1 — LangSmith integration
  [ ] 6.2 — Sentry integration
  [ ] 6.3 — Cost control enforcement

Phase 7: Testing
  [ ] 7.1 — Test configuration
  [ ] 7.2 — Unit tests (9 test files)
  [ ] 7.3 — Integration tests (4 test files)

Phase 8: Docker & Deployment
  [ ] 8.1 — Dockerfile.api
  [ ] 8.2 — Dockerfile.notifier
  [ ] 8.3 — docker-compose.yml (dev)
  [ ] 8.4 — docker-compose.prod.yml

Phase 9: Documentation
  [ ] 9.1 — README.md
  [ ] 9.2 — AGENTS.md
  [ ] 9.3 — API_REFERENCE.md
  [ ] 9.4 — ARCHITECTURE.md
  [ ] 9.5 — CONTRIBUTING.md

Phase 10: Setup Scripts
  [ ] 10.1 — scripts/setup.sh
  [ ] 10.2 — scripts/setup_supabase.sh
  [ ] 10.3 — scripts/run_migrations.sh
  [ ] 10.4 — scripts/generate_vapid_keys.sh
  [ ] 10.5 — scripts/dev.sh
  [ ] 10.6 — scripts/test.sh
```

**Total tasks:** 57 individual implementation items across 11 phases.

---

*Generated from [flux-tsd.md](flux-tsd.md) v2.0 on 2026-02-21.*

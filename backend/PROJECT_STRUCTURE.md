# Backend — Project Structure

This document describes the layout of the `backend/` directory and the purpose of each major component.

---

## Directory Tree

```
backend/
│
├── app/                             # Core FastAPI application package
│   ├── main.py                      # Application entry point; mounts all routers and CORS middleware
│   ├── config.py                    # Application settings via pydantic-settings (reads .env)
│   ├── database.py                  # Supabase client + async SQLAlchemy engine setup
│   └── routers/
│       ├── goals.py                 # Goal CRUD and AI planner endpoints
│       ├── rag.py                   # RAG (Retrieval-Augmented Generation) endpoints
│       └── scheduler.py             # Scheduler agent endpoints
│
├── conv_agent/                      # Conversational (voice) agent — REST control plane
│   ├── router.py                    # /api/v1/voice/* endpoints (session, messages, intents)
│   ├── voice_service.py             # Deepgram session lifecycle management
│   ├── intent_handler.py            # Routes Deepgram function calls to backend services
│   ├── schemas.py                   # Pydantic request/response models for voice API
│   ├── config.py                    # Conv-agent settings (Deepgram key, prompt paths, etc.)
│   └── config/
│       ├── voice_prompt.md          # System prompt loaded at session start
│       └── intents.yaml             # Deepgram function-call intent definitions
│
├── scrum_40_notification_priority_model/  # Sprint feature: notification priority scoring
├── scrum_41_push_notification_integration/ # Sprint feature: Web Push notifications
├── scrum_42_whatsapp_message_integration/  # Sprint feature: WhatsApp messaging
├── scrum_43_phone_call_trigger/            # Sprint feature: VoIP call escalation
├── scrum_44_escalation_demo_ui/            # Sprint feature: escalation demo endpoint
├── scrum_50_pattern_observer/              # Sprint feature: behavioral pattern observer
├── scrum_57_notifier_agent/                # Sprint feature: notifier agent
│
├── tests/                           # Unit + integration tests for app/ routers and services
│   ├── conftest.py
│   ├── test_goal_service.py
│   ├── test_goal_planner_agent.py
│   ├── test_goals_router.py
│   └── test_schemas.py
│
├── conv_agent/tests/                # Unit + integration tests for conv_agent
│   ├── conftest.py
│   ├── test_router.py
│   ├── test_voice_service.py
│   ├── test_intent_handler.py
│   └── test_integration.py
│
├── .env.example                     # Template for required environment variables
├── Dockerfile                       # Python 3.11 slim image; entry: uvicorn app.main:app
├── Makefile                         # Common dev commands (install, dev, test, lint, format)
└── requirements.txt                 # Python dependencies (pinned versions)
```

---

## Core Components

### 1. Application Entry Point (`app/main.py`)

Creates the FastAPI application, registers CORS middleware, and mounts all routers:

- `app.routers.goals` — goal management and AI planner
- `app.routers.rag` — RAG pipeline for context retrieval
- `app.routers.scheduler` — intelligent scheduling agent
- `conv_agent.router` — voice session control plane
- Sprint feature routers (loaded conditionally; missing dependencies produce a startup warning but do not prevent the app from starting)

Health check endpoint: `GET /health` → `{"status": "ok", "service": "flux-backend"}`

### 2. Configuration (`app/config.py`)

Reads environment variables via `pydantic-settings`. Key settings groups:

- **Database:** `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- **AI/LLM:** `OPEN_ROUTER_API_KEY`, `OPENAI_MODEL`, `EMBEDDING_MODEL`
- **RAG (Pinecone):** `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `RAG_TOP_K`
- **Scheduler:** `SCHEDULER_MODEL`, `SCHEDULER_CUTOFF_HOUR`, `SCHEDULER_BUFFER_MINUTES`
- **Server:** `HOST`, `PORT`, `DEBUG`, `CORS_ORIGINS`

### 3. Database Layer (`app/database.py`)

- Initializes the async SQLAlchemy engine using `asyncpg` against `DATABASE_URL`
- Provides the Supabase client (standard key) and admin client (service role key)
- The admin client is used for server-side writes that must bypass Row Level Security (RLS)

### 4. Conversational Agent (`conv_agent/`)

A REST-only control plane that enables voice interactions via Deepgram. It does not run as a separate service — it is mounted directly into the main FastAPI app.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/voice/session` | Start a new voice session; returns a short-lived Deepgram token |
| `POST` | `/api/v1/voice/messages` | Persist a transcript message (fire-and-forget) |
| `GET` | `/api/v1/voice/sessions/{id}/messages` | Retrieve full session transcript |
| `POST` | `/api/v1/voice/intents` | Route a Deepgram function-call intent to the backend |
| `DELETE` | `/api/v1/voice/session/{id}` | Close a session |

**Configuration paths** (`conv_agent/config.py`):
- `voice_prompt_file`: `conv_agent/config/voice_prompt.md` — relative to `WORKDIR=/app` (i.e., the `backend/` directory)
- `voice_intents_file`: `conv_agent/config/intents.yaml` — same base

### 5. Sprint Feature Routers (`scrum_*/`)

Each `scrum_N_*/` directory contains a self-contained feature module developed in a sprint. They are loaded at startup via a `try/except` block in `app/main.py`. If a module fails to load (for example, because `VAPID_PRIVATE_KEY` is not set for push notifications), the app logs a warning and continues without that router.

---

## Data Flow

### Goal Creation

```
POST /goals
    └── goals router
           └── GoalPlannerAgent (OpenRouter / GPT-4o-mini)
                  └── plan stored in Supabase → tasks created
```

### Voice Session

```
POST /api/v1/voice/session
    └── voice_service.build_session_config()
           ├── Loads user context from Supabase
           ├── Builds system prompt from voice_prompt.md
           └── Mints short-lived Deepgram token
               → Returns token + prompt to frontend
               → Frontend connects directly to Deepgram WebSocket

Deepgram emits FunctionCallRequest
    → Frontend POSTs to /api/v1/voice/intents
        └── intent_handler.handle_intent()
               └── Routes to goals / task / scheduler service
```

---

## Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `install` | `make install` | Install production dependencies |
| `dev` | `make dev` | Start uvicorn with auto-reload |
| `test` | `make test` | Run full test suite (`tests/`) |
| `test-unit` | `make test-unit` | Unit tests only |
| `test-integration` | `make test-integration` | Integration tests only (requires Supabase) |
| `lint` | `make lint` | Check formatting and linting |
| `format` | `make format` | Auto-fix formatting issues |

> **Note:** The Makefile `dev` target currently invokes `dao_service.main:app` — use `uvicorn app.main:app --reload` directly until the Makefile is updated.

---

## Key Design Decisions

### Single backend service

The conversational agent (`conv_agent`) is mounted directly into the FastAPI app rather than deployed as a separate microservice. This avoids inter-service HTTP calls in the local dev and Docker Compose environments.

### Async throughout

All database operations use `asyncpg` with SQLAlchemy's async session. The Deepgram token request and Supabase Auth verification use `httpx.AsyncClient`.

### Pydantic v2 models

All request/response schemas use Pydantic v2. `model_config` replaces the old `class Config` inner class.

### RLS-aware admin client

Certain server-side operations (e.g., syncing a Supabase Auth user into `public.users`) require bypassing RLS. These calls use the admin Supabase client initialized with `SUPABASE_SERVICE_ROLE_KEY`.

# Flux Backend — DAO Service

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The **Flux DAO Service** is a framework-agnostic data persistence microservice for all Flux AI agents (Goal Planner, Scheduler, Observer). It exposes a REST API for CRUD operations and contains **no business logic** — that belongs in the calling services.

---

## Architecture

```
backend/
├── dao_service/                          # DAO microservice
│   ├── main.py                          # FastAPI app + exception handlers
│   ├── config.py                        # Pydantic Settings
│   ├── core/                            # database.py, exceptions.py, logging.py
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── user_model.py
│   │   ├── goal_model.py
│   │   ├── task_model.py
│   │   ├── conversation_model.py        # + voice session columns
│   │   ├── message_model.py             # Voice conversation transcripts
│   │   ├── pattern_model.py
│   │   └── notification_log_model.py
│   ├── schemas/                         # Pydantic DTO layer
│   │   ├── user.py, goal.py, task.py
│   │   ├── conversation.py, pattern.py, notification_log.py
│   │   └── pagination.py
│   ├── dao/                             # DAO protocols + SQLAlchemy implementations
│   │   ├── dao_protocols.py
│   │   ├── dao_registry.py
│   │   └── impl/sqlalchemy/
│   ├── services/                        # Data-validation services (no business logic)
│   │   ├── dao_user_service.py
│   │   ├── dao_goal_service.py
│   │   ├── dao_task_service.py
│   │   ├── dao_conversation_service.py
│   │   ├── dao_pattern_service.py
│   │   └── dao_notification_log_service.py
│   ├── api/v1/                          # FastAPI routers
│   │   ├── users_api.py, goals_api.py, tasks_api.py
│   │   ├── conversations_api.py, patterns_api.py
│   │   └── notification_log_api.py
│   ├── tests/
│   │   ├── unit/                        # 103 unit tests (no DB needed)
│   │   └── integration/                 # 49 integration tests (needs Supabase)
│   ├── scripts/
│   │   ├── build_and_test.sh            # Full pipeline: build → unit → Docker → integration
│   │   ├── run_tests.sh                 # Run tests only
│   │   └── setup_dao.sh                 # Environment setup
│   ├── requirements.txt
│   └── requirements-dev.txt
├── Dockerfile
├── docker-compose.dao-service.yml
└── Makefile
```

---

## Entities

| Entity | Table | Description |
|--------|-------|-------------|
| **User** | `users` | User profile — `email`, `onboarded`, `profile`, `notification_preferences` |
| **Goal** | `goals` | User goal — `title`, `class_tags`, `status`, `target_weeks`, `plan_json` |
| **Task** | `tasks` | Schedulable task — `title`, `status`, `trigger_type`, `scheduled_at` |
| **Conversation** | `conversations` | LangGraph thread record — `langgraph_thread_id`, `context_type` + voice columns |
| **Message** | `messages` | Voice conversation transcript — `role`, `content`, `input_modality` |
| **Pattern** | `patterns` | Behavioral signal — `pattern_type`, `data`, `confidence` |
| **NotificationLog** | `notification_log` | Delivery record — `channel`, `sent_at`, `response` |

---

## API Endpoints

All endpoints are prefixed with `/api/v1`. Full OpenAPI docs at `http://localhost:8000/docs`.

| Group | Prefix | Methods |
|-------|--------|---------|
| Users | `/users` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` |
| Goals | `/goals` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` |
| Tasks | `/tasks` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}`, GET `/by-timerange`, GET `/statistics`, POST `/bulk-update-state` |
| Conversations | `/conversations` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, PATCH `/{id}/voice` |
| Messages | `/messages` | POST `/`, GET `/?conversation_id=`, GET `/{id}`, DELETE `/{id}` |
| Patterns | `/patterns` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` |
| Notification Log | `/notification-log` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` |
| Operations | — | GET `/health`, GET `/ready` |

**Task statuses**: `pending`, `done`, `missed`, `rescheduled`, `cancelled`
**Task trigger types**: `time`, `location`
**Goal statuses**: `active`, `completed`, `abandoned`, `pipeline`
**Notification channels**: `push`, `whatsapp`, `call`

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop
- Supabase CLI: `brew install supabase/tap/supabase`

### Local Development

```bash
# 1. Start Supabase
supabase start

# 2. Create and activate virtual environment
cd backend
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r dao_service/requirements.txt
pip install -r dao_service/requirements-dev.txt

# 4. Create .env (if not present)
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres

# 5. Start the service
make dev
```

API available at `http://localhost:8000` — Swagger UI at `http://localhost:8000/docs`.

### Running via Docker

```bash
docker build -t flux-dao-service backend/
docker compose -f backend/docker-compose.dao-service.yml up -d
curl http://localhost:8000/health
```

---

## Testing

```bash
cd backend

# Unit tests only (no database, ~0.5s)
pytest dao_service/tests/unit/ -v

# Integration tests (needs Supabase on port 54322)
pytest dao_service/tests/integration/ -v

# Full suite with coverage
pytest dao_service/tests/ --cov=dao_service --cov-report=term-missing

# Complete pipeline (build → unit → Docker deploy → integration → report)
bash dao_service/scripts/build_and_test.sh
```

**Test counts**: 103 unit tests + 49 integration tests = 152 total.

---

## Design

See [`docs/dao_design.md`](../docs/dao_design.md) for the full architecture document covering:
- `DatabaseSession` protocol for ORM-agnostic layers
- DAO protocol interfaces and SQLAlchemy implementations
- Factory / Registry pattern for ORM switching
- ACID transaction support via Unit of Work
- Layer responsibilities (ORM → DTO → DAO → Service → API)

See [`docs/user_guide_dao.md`](../docs/user_guide_dao.md) for integration examples (REST HTTP and direct Python API).

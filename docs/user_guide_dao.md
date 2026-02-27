# Flux DAO Service User Guide

**Version**: 1.2
**Date**: 2026-02-23

This guide explains how to use the Flux Data Access (DAO) Service from other microservices. The DAO Service is an internal microservice that provides data persistence and retrieval for all Flux AI agents (Goal Planner, Scheduler, Observer).

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Method 1: REST API Integration](#method-1-rest-api-integration)
4. [Method 2: Direct Python API Integration](#method-2-direct-python-api-integration)
5. [API Reference](#api-reference)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The DAO Service is a **data-only microservice** — it handles CRUD operations and data validation but contains **no business logic**. Business logic belongs in the calling services (Goal Planner, Scheduler, Observer).

### Key Characteristics

- **Framework-agnostic**: Uses a `DatabaseSession` protocol that allows switching ORM frameworks
- **Data validation only**: Validates data format and referential integrity
- **ACID transactions**: Full transaction support via Unit of Work pattern
- **No authentication required**: Internal microservice with no `X-Flux-Service-Key` requirement in the current build

### Entities Managed

| Entity | Description |
|--------|-------------|
| **Users** | User profiles: `email`, `onboarded`, `profile`, `notification_preferences` |
| **Goals** | User goals: `title`, `class_tags`, `status`, `target_weeks`, `plan_json` |
| **Tasks** | Individual tasks: `title`, `status`, `trigger_type`, `scheduled_at` |
| **Conversations** | LangGraph thread records: `langgraph_thread_id`, `context_type` |
| **Patterns** | Behavioral signals: `pattern_type`, `data`, `confidence` |
| **NotificationLog** | Delivery records: `channel`, `sent_at`, `response` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Calling Service                              │
│            (Goal Planner / Scheduler / Observer)                 │
│                                                                  │
│   ┌─────────────────┐              ┌─────────────────┐          │
│   │  REST Client    │              │  Direct Python  │          │
│   │  (httpx)        │              │  API Import     │          │
│   └────────┬────────┘              └────────┬────────┘          │
└────────────┼────────────────────────────────┼────────────────────┘
             │ HTTP                           │ In-process
             ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DAO Service                                 │
│                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │ API      │→ │ Service  │→ │ DAO      │→ │ Models   │       │
│   │ (FastAPI)│  │ Layer    │  │ Layer    │  │ (ORM)    │       │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                  │
│   Port 8000 (internal network only)                             │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL (Supabase)                         │
│                    Port 54322 (local dev)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Method 1: REST API Integration

Use HTTP calls when calling from a **separate microservice** (different container/process). This is the recommended approach for production deployments.

### Prerequisites

- DAO Service running (Docker or local)
- `httpx` library for async HTTP calls

### Base URL

| Environment | URL |
|-------------|-----|
| Docker (internal) | `http://flux-dao-service:8000` |
| Local development | `http://localhost:8000` |

### Basic HTTP Client Setup

```python
import httpx

class DaoClient:
    """HTTP client for the DAO Service."""

    def __init__(self, base_url: str = "http://flux-dao-service:8000"):
        self.base_url = base_url

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
```

### Example: Goal Planner Flow

```python
import httpx
from datetime import datetime, timezone

DAO_SERVICE_URL = "http://flux-dao-service:8000"

async def create_goal_with_tasks(user_email: str, goal_title: str):
    """Goal Planner: Create a user, goal, and tasks."""
    async with httpx.AsyncClient(base_url=DAO_SERVICE_URL, timeout=30.0) as client:

        # Step 1: Create a user
        user_resp = await client.post("/api/v1/users/", json={
            "email": user_email,
            "onboarded": False,
        })
        user_resp.raise_for_status()
        user_id = user_resp.json()["id"]
        print(f"Created user: {user_id}")

        # Step 2: Create a goal
        goal_resp = await client.post("/api/v1/goals/", json={
            "user_id": user_id,
            "title": goal_title,
            "class_tags": ["health"],
            "target_weeks": 8,
            "status": "active",
        })
        goal_resp.raise_for_status()
        goal_id = goal_resp.json()["id"]
        print(f"Created goal: {goal_id}")

        # Step 3: Create tasks linked to the goal
        task_resp = await client.post("/api/v1/tasks/", json={
            "user_id": user_id,
            "goal_id": goal_id,
            "title": "Run 3km",
            "trigger_type": "time",
            "status": "pending",
        })
        task_resp.raise_for_status()
        print(f"Created task: {task_resp.json()['id']}")

import asyncio
asyncio.run(create_goal_with_tasks("jane@example.com", "Run a half marathon"))
```

### Example: Scheduler Service Flow

```python
import httpx
from datetime import datetime, timezone

DAO_SERVICE_URL = "http://flux-dao-service:8000"

async def scheduler_daily_sync(user_id: str):
    """Scheduler: Query tasks, detect missed ones, bulk update status."""
    async with httpx.AsyncClient(base_url=DAO_SERVICE_URL) as client:

        # Step 1: Get tasks for today's time window
        now = datetime.now(timezone.utc)
        start_at = now.replace(hour=0, minute=0, second=0).isoformat()
        end_at = now.replace(hour=23, minute=59, second=59).isoformat()

        tasks_resp = await client.get(
            "/api/v1/tasks/by-timerange",
            params={"user_id": user_id, "start_at": start_at, "end_at": end_at},
        )
        tasks_resp.raise_for_status()
        tasks = tasks_resp.json()
        print(f"Found {len(tasks)} tasks for today")

        # Step 2: Identify missed tasks (business logic in Scheduler)
        missed_ids = []
        for task in tasks:
            if task["status"] == "pending":
                scheduled = task.get("scheduled_at")
                if scheduled and datetime.fromisoformat(scheduled) < now:
                    missed_ids.append(task["id"])

        # Step 3: Bulk update missed tasks
        if missed_ids:
            bulk_resp = await client.post(
                "/api/v1/tasks/bulk-update-state",
                json={"task_ids": missed_ids, "new_status": "missed"},
            )
            bulk_resp.raise_for_status()
            print(f"Marked {bulk_resp.json()['updated_count']} tasks as missed")

        return {"tasks_checked": len(tasks), "missed": len(missed_ids)}
```

### Example: Observer Service Flow

```python
import httpx
from datetime import datetime, timedelta, timezone

DAO_SERVICE_URL = "http://flux-dao-service:8000"

async def analyze_user_patterns(user_id: str, days: int = 30):
    """Observer: Get task statistics for pattern analysis."""
    async with httpx.AsyncClient(base_url=DAO_SERVICE_URL) as client:

        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).isoformat()

        stats_resp = await client.get(
            "/api/v1/tasks/statistics",
            params={"user_id": user_id, "start_date": start_date, "end_date": now.isoformat()},
        )
        stats_resp.raise_for_status()
        stats = stats_resp.json()

        print(f"User {user_id} — Past {days} days:")
        print(f"  Total tasks: {stats['total_tasks']}")
        print(f"  Completion rate: {stats['completion_rate'] * 100:.1f}%")
        print(f"  By status: {stats['by_status']}")

        # Business logic: Detect patterns (done in Observer, not DAO)
        if stats["completion_rate"] < 0.5:
            print("  Low completion rate detected")

        return stats
```

---

## Method 2: Direct Python API Integration

Use direct imports when the calling service runs **in the same Python process** as the DAO Service.

### Prerequisites

- DAO Service code available in Python path
- `DATABASE_URL` environment variable set
- `asyncpg`, `sqlalchemy`, and `pydantic` installed

### Setup

```bash
pip install -r backend/dao_service/requirements.txt
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"
```

### Basic Direct API Usage

```python
from dao_service.core.database import AsyncSessionLocal
from dao_service.services.dao_user_service import DaoUserService
from dao_service.services.dao_goal_service import DaoGoalService
from dao_service.schemas.user import UserCreateDTO
from dao_service.schemas.goal import GoalCreateDTO


async def direct_api_example():
    async with AsyncSessionLocal() as db:
        try:
            user_service = DaoUserService()
            goal_service = DaoGoalService()

            # Create a user
            user = await user_service.create_user(
                db,
                UserCreateDTO(email="direct@example.com"),
            )
            print(f"Created user: {user.id}")

            # Create a goal
            goal = await goal_service.create_goal(
                db,
                GoalCreateDTO(
                    user_id=user.id,
                    title="Learn Spanish",
                    class_tags=["education"],
                    target_weeks=12,
                ),
            )
            print(f"Created goal: {goal.id}")

            await db.commit()
            return goal

        except Exception:
            await db.rollback()
            raise


import asyncio
asyncio.run(direct_api_example())
```

### Using the Unit of Work Pattern

For operations spanning multiple entities where all-or-nothing atomicity is required:

```python
from dao_service.core.database import AsyncSessionLocal
from dao_service.repositories.dao_unit_of_work import DaoUnitOfWork
from dao_service.schemas.user import UserCreateDTO
from dao_service.schemas.goal import GoalCreateDTO
from dao_service.schemas.task import TaskCreateDTO


async def atomic_multi_entity_creation():
    async with AsyncSessionLocal() as db:
        async with DaoUnitOfWork(db) as uow:
            user = await uow.users.create(db, UserCreateDTO(email="uow@example.com"))
            goal = await uow.goals.create(
                db, GoalCreateDTO(user_id=user.id, title="Test Goal")
            )
            task = await uow.tasks.create(
                db,
                TaskCreateDTO(user_id=user.id, goal_id=goal.id, title="First Task"),
            )
            # If any step fails, UoW.__aexit__ triggers rollback

        await db.commit()
        return {"user": user, "goal": goal, "task": task}
```

---

## API Reference

### Base URL & Authentication

| Item | Value |
|------|-------|
| Base URL (Docker) | `http://flux-dao-service:8000` |
| Base URL (local) | `http://localhost:8000` |
| Content-Type | `application/json` |

### User Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users/` | List users (paginated) |
| GET | `/api/v1/users/{user_id}` | Get user by ID |
| POST | `/api/v1/users/` | Create user |
| PATCH | `/api/v1/users/{user_id}` | Update user |
| DELETE | `/api/v1/users/{user_id}` | Delete user (cascades) |

**Create User Request:**
```json
{
  "email": "jane@example.com",
  "onboarded": false,
  "profile": {"timezone": "America/New_York"},
  "notification_preferences": {"whatsapp": true}
}
```

### Goal Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/goals/` | List goals (paginated) |
| GET | `/api/v1/goals/{goal_id}` | Get goal by ID |
| POST | `/api/v1/goals/` | Create goal |
| PATCH | `/api/v1/goals/{goal_id}` | Update goal |
| DELETE | `/api/v1/goals/{goal_id}` | Delete goal (cascades) |

**Create Goal Request:**
```json
{
  "user_id": "uuid",
  "title": "Learn Python",
  "description": "Master Python fundamentals",
  "class_tags": ["education", "skills"],
  "target_weeks": 8,
  "status": "active"
}
```

**Goal statuses**: `active`, `completed`, `abandoned`, `pipeline`

### Task Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tasks/` | List tasks (paginated) |
| GET | `/api/v1/tasks/{task_id}` | Get task by ID |
| POST | `/api/v1/tasks/` | Create task |
| PATCH | `/api/v1/tasks/{task_id}` | Update task |
| DELETE | `/api/v1/tasks/{task_id}` | Delete task |
| GET | `/api/v1/tasks/by-timerange` | **Scheduler**: Get tasks in time window |
| GET | `/api/v1/tasks/statistics` | **Observer**: Get task statistics |
| POST | `/api/v1/tasks/bulk-update-state` | **Scheduler**: Bulk status update |

**Task statuses**: `pending`, `done`, `missed`, `rescheduled`, `cancelled`
**Trigger types**: `time`, `location`

**Create Task Request:**
```json
{
  "user_id": "uuid",
  "goal_id": "uuid",
  "title": "Run 3km",
  "status": "pending",
  "trigger_type": "time",
  "scheduled_at": "2026-03-01T09:00:00Z",
  "duration_minutes": 30
}
```

**By-Timerange Query Parameters:** `user_id`, `start_at` (ISO datetime), `end_at` (ISO datetime)

**Bulk Update Status Request:**
```json
{
  "task_ids": ["uuid1", "uuid2"],
  "new_status": "missed"
}
```

**Statistics Query Parameters:** `user_id`, `start_date` (ISO datetime), `end_date` (ISO datetime)

**Statistics Response:**
```json
{
  "user_id": "uuid",
  "total_tasks": 42,
  "by_status": {
    "done": 25,
    "pending": 10,
    "missed": 5,
    "rescheduled": 2,
    "cancelled": 0
  },
  "completion_rate": 0.5952
}
```

### Conversation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/conversations/` | List conversations |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| POST | `/api/v1/conversations/` | Create conversation |
| PATCH | `/api/v1/conversations/{id}` | Update conversation |

**Context types**: `goal`, `task`, `onboarding`, `reschedule`

**Create Conversation Request:**
```json
{
  "user_id": "uuid",
  "langgraph_thread_id": "thread-abc123",
  "context_type": "goal"
}
```

### Pattern Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/patterns/` | List patterns |
| GET | `/api/v1/patterns/{id}` | Get pattern |
| POST | `/api/v1/patterns/` | Create pattern |
| PATCH | `/api/v1/patterns/{id}` | Update pattern |
| DELETE | `/api/v1/patterns/{id}` | Delete pattern |

### Notification Log Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notification-log/` | List log entries |
| GET | `/api/v1/notification-log/{id}` | Get log entry |
| POST | `/api/v1/notification-log/` | Create log entry |
| PATCH | `/api/v1/notification-log/{id}` | Update log entry |
| DELETE | `/api/v1/notification-log/{id}` | Delete log entry |

**Channels**: `push`, `whatsapp`, `call`

### Operational Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (checks DB) |

### Pagination Response Format

All list endpoints return paginated responses:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 100,
  "has_next": false,
  "has_prev": false
}
```

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

| Status Code | Meaning |
|-------------|---------|
| 200 | Success (GET, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad request / validation error |
| 404 | Entity not found |
| 409 | Conflict (unique constraint violation) |
| 422 | Unprocessable entity (invalid field value) |
| 500 | Internal server error |

---

## Testing

### Running the Test Suite

```bash
cd backend

# Install development dependencies
pip install -r dao_service/requirements-dev.txt

# Run all DAO service tests
pytest dao_service/tests/ -v

# Unit tests only (no database required, fast)
pytest dao_service/tests/unit/ -v

# Integration tests only (requires Supabase PostgreSQL)
pytest dao_service/tests/integration/ -v

# Run tests with coverage report
pytest dao_service/tests/ --cov=dao_service --cov-report=html

# Full pipeline: build → unit tests → Docker deploy → integration tests → XML report
bash dao_service/scripts/build_and_test.sh
```

### Prerequisites for Integration Tests

1. **Docker Desktop** running
2. **Supabase local instance** running on port 54322:
   ```bash
   supabase start
   ```
3. **Database migrations applied**:
   ```bash
   bash scripts/supabase_setup.sh
   ```

### Testing with REST API (Using Swagger UI)

1. Start the development server:
   ```bash
   cd backend && make dev
   ```

2. Open Swagger UI: http://localhost:8000/docs

3. Try the endpoints interactively.

### Testing with Docker

```bash
# Build and deploy
docker compose -f backend/docker-compose.dao-service.yml up -d

# Check health
curl http://localhost:8000/health

# Test an endpoint
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# View logs
docker logs flux-dao-service

# Stop
docker compose -f backend/docker-compose.dao-service.yml down
```

### Writing Your Own Tests

#### Integration Test Pattern (HTTP)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestMyFeature:
    async def test_create_and_retrieve_task(self, client: AsyncClient):
        # Create a user first
        user_resp = await client.post("/api/v1/users/", json={"email": "test@example.com"})
        user_id = user_resp.json()["id"]

        goal_resp = await client.post("/api/v1/goals/", json={
            "user_id": user_id, "title": "Test Goal",
        })
        goal_id = goal_resp.json()["id"]

        # Create task
        task_resp = await client.post("/api/v1/tasks/", json={
            "user_id": user_id,
            "goal_id": goal_id,
            "title": "Test Task",
            "trigger_type": "time",
        })
        assert task_resp.status_code == 201
        task = task_resp.json()

        # Verify retrieval
        get_resp = await client.get(f"/api/v1/tasks/{task['id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == "Test Task"
```

#### Unit Test Pattern (Schema Validation)

```python
import pytest
from dao_service.schemas.task import TaskCreateDTO
from uuid import uuid4

def test_task_create_dto_validation():
    # Valid DTO
    dto = TaskCreateDTO(
        user_id=uuid4(),
        title="Valid task",
        trigger_type="time",
    )
    assert dto.title == "Valid task"

    # Invalid: unknown status
    with pytest.raises(ValueError):
        TaskCreateDTO(user_id=uuid4(), title="Task", status="scheduled")  # not a valid status
```

### Test Configuration

The test suite uses these fixtures from `backend/dao_service/tests/conftest.py`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `test_engine` | session | Async SQLAlchemy engine (NullPool for tests) |
| `setup_database` | session | Truncates tables before tests |
| `db_session` | function | Fresh session per test |
| `client` | function | Async HTTP client (ASGITransport, no server needed) |

### Test Data Factories

```python
from dao_service.tests.conftest import make_user_data, make_goal_data, make_task_data

user_data = make_user_data()
goal_data = make_goal_data(user_id)
task_data = make_task_data(user_id, goal_id)
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Connection refused` on port 8000 | DAO Service not running | Start with `make dev` or Docker |
| `Connection refused` on port 54322 | Supabase not running | Run `supabase start` |
| `404 Not Found` | Entity doesn't exist | Verify UUID is correct |
| `409 Conflict` | Duplicate unique field | Check `langgraph_thread_id` or other unique constraints |
| `422 Unprocessable Entity` | Invalid field value | Check enum values (status, trigger_type, etc.) |
| Tests hang | Event loop binding issue | Use `pytest-asyncio` correctly |
| `asyncpg` build fails | Missing system libs | Use binary wheel: `pip install --only-binary=:all: asyncpg` |

### Checking Service Health

```bash
curl http://localhost:8000/health   # liveness
curl http://localhost:8000/ready    # readiness (checks DB)
```

### Database Connection Issues

```bash
# Local development
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

# Docker (uses host.docker.internal)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:54322/postgres
```

### Resetting Test Database

```bash
supabase db reset
# or manually:
psql "postgresql://postgres:postgres@localhost:54322/postgres" -c "TRUNCATE users CASCADE;"
```

---

## Additional Resources

- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Design Document**: `docs/dao_design.md`
- **Test Examples**: `backend/dao_service/tests/integration/test_api/`

---

**Document End**

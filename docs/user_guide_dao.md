# Flux DAO Service User Guide

**Version**: 1.0  
**Date**: 2026-02-15

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
- **Service-to-service authentication**: Uses API keys via `X-Flux-Service-Key` header

### Entities Managed

| Entity | Description |
|--------|-------------|
| **Users** | User profiles with preferences |
| **Goals** | User goals with category, timeline, status |
| **Milestones** | Weekly milestones within goals |
| **Tasks** | Individual tasks with scheduling info |
| **Conversations** | Conversation history (JSONB messages) |
| **DemoFlags** | Demo/simulation configuration per user |

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
- Valid service API key
- `httpx` library for async HTTP calls

### Authentication

All endpoints require the `X-Flux-Service-Key` header. Valid keys are configured via the `SERVICE_API_KEYS` environment variable.

**Default development keys**:
- `goal-planner-key-abc`
- `scheduler-key-def`
- `observer-key-ghi`

### Base URL

| Environment | URL |
|-------------|-----|
| Docker (internal) | `http://flux-dao-service:8000` |
| Local development | `http://localhost:8000` |

### Basic HTTP Client Setup

```python
import httpx
from typing import Optional

class DaoClient:
    """HTTP client for the DAO Service."""
    
    def __init__(
        self,
        base_url: str = "http://flux-dao-service:8000",
        service_key: str = "goal-planner-key-abc",
    ):
        self.base_url = base_url
        self.headers = {"X-Flux-Service-Key": service_key}
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
        ) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
```

### Example: Complete Goal Planner Flow

```python
import httpx
from datetime import datetime, timezone
from uuid import UUID

DAO_SERVICE_URL = "http://flux-dao-service:8000"
SERVICE_KEY = "goal-planner-key-abc"

async def create_goal_with_plan(user_email: str, goal_title: str):
    """
    Goal Planner: Create a user, goal, milestones, and tasks atomically.
    """
    headers = {"X-Flux-Service-Key": SERVICE_KEY}
    
    async with httpx.AsyncClient(
        base_url=DAO_SERVICE_URL,
        headers=headers,
        timeout=30.0,
    ) as client:
        
        # Step 1: Create a user
        user_resp = await client.post("/api/v1/users/", json={
            "name": "Jane Doe",
            "email": user_email,
            "preferences": {"timezone": "America/New_York"},
            "demo_mode": False,
        })
        user_resp.raise_for_status()
        user = user_resp.json()
        user_id = user["id"]
        print(f"Created user: {user_id}")
        
        # Step 2: Create goal with full structure (atomic transaction)
        goal_resp = await client.post("/api/v1/goals/with-structure", json={
            "goal": {
                "user_id": user_id,
                "title": goal_title,
                "category": "health",
                "timeline": "8 weeks",
                "status": "active",
            },
            "milestones": [
                {
                    "week_number": 1,
                    "title": "Build base fitness",
                    "status": "pending",
                    "tasks": [
                        {
                            "title": "Run 3km",
                            "state": "scheduled",
                            "priority": "standard",
                            "trigger_type": "time",
                            "is_recurring": True,
                        },
                        {
                            "title": "Stretch routine (15 min)",
                            "state": "scheduled",
                            "priority": "standard",
                            "trigger_type": "time",
                            "is_recurring": True,
                        },
                    ],
                },
                {
                    "week_number": 2,
                    "title": "Increase distance",
                    "status": "pending",
                    "tasks": [
                        {
                            "title": "Run 5km",
                            "state": "scheduled",
                            "priority": "important",
                            "trigger_type": "time",
                            "is_recurring": True,
                        },
                    ],
                },
            ],
        })
        goal_resp.raise_for_status()
        goal = goal_resp.json()
        
        print(f"Created goal: {goal['id']}")
        print(f"  Milestones: {len(goal['milestones'])}")
        print(f"  Tasks: {len(goal['tasks'])}")
        
        return goal

# Run the example
import asyncio
asyncio.run(create_goal_with_plan("jane@example.com", "Run a half marathon"))
```

### Example: Scheduler Service Flow

```python
import httpx
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

DAO_SERVICE_URL = "http://flux-dao-service:8000"
SERVICE_KEY = "scheduler-key-def"

async def scheduler_daily_sync(user_id: str):
    """
    Scheduler: Query tasks, detect drift, bulk update states.
    """
    headers = {"X-Flux-Service-Key": SERVICE_KEY}
    
    async with httpx.AsyncClient(
        base_url=DAO_SERVICE_URL,
        headers=headers,
    ) as client:
        
        # Step 1: Get tasks for today's time window
        now = datetime.now(timezone.utc)
        start_time = now.replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
        
        tasks_resp = await client.get(
            "/api/v1/tasks/by-timerange",
            params={
                "user_id": user_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )
        tasks_resp.raise_for_status()
        tasks = tasks_resp.json()
        print(f"Found {len(tasks)} tasks for today")
        
        # Step 2: Identify drifted tasks (business logic in Scheduler)
        drifted_task_ids = []
        for task in tasks:
            if task["state"] == "scheduled":
                task_end = datetime.fromisoformat(task["end_time"]) if task["end_time"] else None
                if task_end and task_end < now:
                    drifted_task_ids.append(task["id"])
        
        # Step 3: Bulk update drifted tasks
        if drifted_task_ids:
            bulk_resp = await client.post(
                "/api/v1/tasks/bulk-update-state",
                json={
                    "task_ids": drifted_task_ids,
                    "new_state": "drifted",
                },
            )
            bulk_resp.raise_for_status()
            result = bulk_resp.json()
            print(f"Marked {result['updated_count']} tasks as drifted")
        
        return {"tasks_checked": len(tasks), "drifted": len(drifted_task_ids)}


async def link_calendar_event(task_id: str, calendar_event_id: str):
    """
    Scheduler: After creating a Google Calendar event, link it to the task.
    """
    headers = {"X-Flux-Service-Key": SERVICE_KEY}
    
    async with httpx.AsyncClient(
        base_url=DAO_SERVICE_URL,
        headers=headers,
    ) as client:
        resp = await client.patch(
            f"/api/v1/tasks/{task_id}/calendar-event",
            json={"calendar_event_id": calendar_event_id},
        )
        resp.raise_for_status()
        return resp.json()
```

### Example: Observer Service Flow

```python
import httpx
from datetime import datetime, timedelta, timezone

DAO_SERVICE_URL = "http://flux-dao-service:8000"
SERVICE_KEY = "observer-key-ghi"

async def analyze_user_patterns(user_id: str, days: int = 30):
    """
    Observer: Get task statistics for pattern analysis.
    """
    headers = {"X-Flux-Service-Key": SERVICE_KEY}
    
    async with httpx.AsyncClient(
        base_url=DAO_SERVICE_URL,
        headers=headers,
    ) as client:
        
        # Get statistics for the past N days
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        
        stats_resp = await client.get(
            "/api/v1/tasks/statistics",
            params={
                "user_id": user_id,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
            },
        )
        stats_resp.raise_for_status()
        stats = stats_resp.json()
        
        print(f"User {user_id} - Past {days} days:")
        print(f"  Total tasks: {stats['total_tasks']}")
        print(f"  Completion rate: {stats['completion_rate'] * 100:.1f}%")
        print(f"  By state: {stats['by_state']}")
        
        # Business logic: Detect patterns (done in Observer, not DAO)
        if stats["completion_rate"] < 0.5:
            print("  ⚠️  Low completion rate detected")
        
        return stats
```

---

## Method 2: Direct Python API Integration

Use direct imports when the calling service runs **in the same Python process** as the DAO Service, or when you want to avoid HTTP overhead (e.g., during testing, batch jobs, or monolithic deployments).

### Prerequisites

- DAO Service code available in Python path
- Database connection configured via environment variables
- `asyncpg`, `sqlalchemy`, and `pydantic` installed

### Setup

```bash
# Install DAO service dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"
```

### Basic Direct API Usage

```python
from dao_service.core.database import AsyncSessionLocal, DatabaseSession
from dao_service.services.dao_user_service import DaoUserService
from dao_service.services.dao_goal_service import DaoGoalService
from dao_service.services.dao_task_service import DaoTaskService
from dao_service.schemas.user import UserCreateDTO
from dao_service.schemas.goal import GoalCreateDTO, GoalStructureCreateDTO, MilestoneStructureDTO, TaskStructureDTO
from dao_service.schemas.task import TaskCreateDTO


async def direct_api_example():
    """
    Direct Python API usage — no HTTP overhead.
    """
    # Get a database session
    async with AsyncSessionLocal() as db:
        try:
            # Initialize services
            user_service = DaoUserService()
            goal_service = DaoGoalService()
            
            # Create a user
            user = await user_service.create_user(
                db,
                UserCreateDTO(
                    name="Direct API User",
                    email="direct@example.com",
                    preferences={"theme": "dark"},
                    demo_mode=False,
                ),
            )
            print(f"Created user: {user.id}")
            
            # Create a goal with structure (atomic transaction)
            goal_with_relations = await goal_service.create_goal_with_structure(
                db,
                GoalStructureCreateDTO(
                    goal=GoalCreateDTO(
                        user_id=user.id,
                        title="Learn Spanish",
                        category="education",
                        timeline="12 weeks",
                    ),
                    milestones=[
                        MilestoneStructureDTO(
                            week_number=1,
                            title="Basic vocabulary",
                            tasks=[
                                TaskStructureDTO(title="Learn 50 common words"),
                                TaskStructureDTO(title="Practice pronunciation"),
                            ],
                        ),
                    ],
                ),
            )
            
            print(f"Created goal: {goal_with_relations.id}")
            print(f"  Milestones: {len(goal_with_relations.milestones)}")
            print(f"  Tasks: {len(goal_with_relations.tasks)}")
            
            # Commit is automatic via session context manager
            await db.commit()
            
            return goal_with_relations
            
        except Exception as e:
            await db.rollback()
            raise


# Run the example
import asyncio
asyncio.run(direct_api_example())
```

### Using the Unit of Work Pattern

For complex operations that span multiple entities, use the `DaoUnitOfWork` class:

```python
from dao_service.core.database import AsyncSessionLocal
from dao_service.repositories.dao_unit_of_work import DaoUnitOfWork
from dao_service.schemas.user import UserCreateDTO
from dao_service.schemas.goal import GoalCreateDTO
from dao_service.schemas.milestone import MilestoneCreateDTO
from dao_service.schemas.task import TaskCreateDTO


async def atomic_multi_entity_creation():
    """
    Use Unit of Work for atomic multi-entity operations.
    If any operation fails, ALL changes are rolled back.
    """
    async with AsyncSessionLocal() as db:
        async with DaoUnitOfWork(db) as uow:
            # All operations share the same transaction
            user = await uow.users.create(
                db,
                UserCreateDTO(
                    name="UoW Test User",
                    email="uow@example.com",
                ),
            )
            
            goal = await uow.goals.create(
                db,
                GoalCreateDTO(
                    user_id=user.id,
                    title="Test Goal",
                    category="test",
                ),
            )
            
            milestone = await uow.milestones.create(
                db,
                MilestoneCreateDTO(
                    goal_id=goal.id,
                    week_number=1,
                    title="First Week",
                ),
            )
            
            task = await uow.tasks.create(
                db,
                TaskCreateDTO(
                    user_id=user.id,
                    goal_id=goal.id,
                    milestone_id=milestone.id,
                    title="First Task",
                ),
            )
            
            # If we reach here without exception, changes persist
            # If any step fails, UoW.__aexit__ triggers rollback
            
        # After exiting UoW context, commit via db session
        await db.commit()
        
        return {"user": user, "goal": goal, "milestone": milestone, "task": task}
```

### Direct DAO Access (Low-Level)

For maximum control, access DAOs directly:

```python
from dao_service.core.database import AsyncSessionLocal
from dao_service.dao.dao_registry import get_task_dao, get_user_dao
from dao_service.schemas.task import TaskCreateDTO, TaskUpdateDTO
from dao_service.schemas.enums import TaskState
from datetime import datetime, timezone
from uuid import UUID


async def low_level_dao_access():
    """
    Direct DAO access for fine-grained control.
    """
    task_dao = get_task_dao()
    
    async with AsyncSessionLocal() as db:
        # Assuming user_id and goal_id exist
        user_id = UUID("...")  # existing user
        goal_id = UUID("...")  # existing goal
        
        # Create a task
        task = await task_dao.create(
            db,
            TaskCreateDTO(
                user_id=user_id,
                goal_id=goal_id,
                title="DAO-level task",
                state=TaskState.SCHEDULED,
            ),
        )
        
        # Query tasks by time range
        now = datetime.now(timezone.utc)
        tasks = await task_dao.get_tasks_by_user_and_timerange(
            db,
            user_id=user_id,
            start_time=now,
            end_time=now.replace(hour=23, minute=59),
        )
        
        # Bulk update states
        task_ids = [t.id for t in tasks]
        updated_count = await task_dao.bulk_update_state(
            db,
            task_ids=task_ids,
            new_state=TaskState.COMPLETED,
        )
        
        # Get statistics
        stats = await task_dao.get_task_statistics(
            db,
            user_id=user_id,
            start_date=now.replace(day=1),
            end_date=now,
        )
        
        await db.commit()
        
        return {"task": task, "updated": updated_count, "stats": stats}
```

---

## API Reference

### Base URL & Authentication

| Item | Value |
|------|-------|
| Base URL (Docker) | `http://flux-dao-service:8000` |
| Base URL (local) | `http://localhost:8000` |
| Auth Header | `X-Flux-Service-Key: <key>` |
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
  "name": "Jane Doe",
  "email": "jane@example.com",
  "preferences": {"timezone": "America/New_York"},
  "demo_mode": false
}
```

### Goal Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/goals/` | List goals (paginated) |
| GET | `/api/v1/goals/{goal_id}` | Get goal by ID |
| GET | `/api/v1/goals/{goal_id}/full` | Get goal with milestones & tasks |
| POST | `/api/v1/goals/` | Create goal |
| POST | `/api/v1/goals/with-structure` | Create goal + milestones + tasks atomically |
| PATCH | `/api/v1/goals/{goal_id}` | Update goal |
| DELETE | `/api/v1/goals/{goal_id}` | Delete goal (cascades) |

**Create Goal with Structure Request:**
```json
{
  "goal": {
    "user_id": "uuid",
    "title": "Learn Python",
    "category": "education",
    "timeline": "8 weeks",
    "status": "active"
  },
  "milestones": [
    {
      "week_number": 1,
      "title": "Basics",
      "status": "pending",
      "tasks": [
        {
          "title": "Complete tutorial",
          "state": "scheduled",
          "priority": "standard",
          "trigger_type": "time",
          "is_recurring": false
        }
      ]
    }
  ]
}
```

### Task Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tasks/` | List tasks (paginated) |
| GET | `/api/v1/tasks/{task_id}` | Get task by ID |
| POST | `/api/v1/tasks/` | Create task |
| PATCH | `/api/v1/tasks/{task_id}` | Update task |
| DELETE | `/api/v1/tasks/{task_id}` | Delete task |
| GET | `/api/v1/tasks/by-timerange` | **Scheduler**: Get tasks in time window |
| POST | `/api/v1/tasks/bulk-update-state` | **Scheduler**: Bulk state update |
| PATCH | `/api/v1/tasks/{task_id}/calendar-event` | **Scheduler**: Link calendar event |
| GET | `/api/v1/tasks/statistics` | **Observer**: Get task statistics |

**Task States**: `scheduled`, `drifted`, `completed`, `missed`

**Task Priorities**: `standard`, `important`, `must-not-miss`

**Trigger Types**: `time`, `on_leaving_home`

**Bulk Update State Request:**
```json
{
  "task_ids": ["uuid1", "uuid2"],
  "new_state": "drifted"
}
```

**Statistics Response:**
```json
{
  "user_id": "uuid",
  "total_tasks": 42,
  "by_state": {
    "scheduled": 10,
    "completed": 25,
    "drifted": 5,
    "missed": 2
  },
  "completion_rate": 0.5952
}
```

### Milestone Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/milestones/` | List milestones |
| GET | `/api/v1/milestones/{milestone_id}` | Get milestone |
| POST | `/api/v1/milestones/` | Create milestone |
| PATCH | `/api/v1/milestones/{milestone_id}` | Update milestone |
| DELETE | `/api/v1/milestones/{milestone_id}` | Delete milestone |

### Conversation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/conversations/` | List conversations |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| POST | `/api/v1/conversations/` | Create conversation |
| PATCH | `/api/v1/conversations/{id}` | Update conversation |

### Demo Flag Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/demo-flags/{user_id}` | Get demo flags |
| PUT | `/api/v1/demo-flags/{user_id}` | Set/update demo flags |

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
| 403 | Invalid or missing service key |
| 404 | Entity not found |
| 422 | Unprocessable entity (FK violation) |
| 500 | Internal server error |

---

## Testing

### Running the Test Suite

The DAO Service includes comprehensive unit and integration tests.

```bash
cd backend

# Install development dependencies
make install-dev

# Run all tests
make test

# Run unit tests only (no database required, fast)
make test-unit

# Run integration tests only (requires Supabase PostgreSQL)
make test-integration

# Run tests with verbose output
pytest tests/ -v

# Run tests with coverage report
pytest tests/ --cov=dao_service --cov-report=html
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

3. Click **Authorize** and enter a service key:
   ```
   goal-planner-key-abc
   ```

4. Try the endpoints interactively

### Testing with Docker

```bash
# Build and deploy
docker-compose -f backend/docker-compose.dao-service.yml up -d

# Check health
curl http://localhost:8000/health

# Test an endpoint
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -H "X-Flux-Service-Key: goal-planner-key-abc" \
  -d '{"name": "Test User", "email": "test@example.com"}'

# View logs
docker logs flux-dao-service

# Stop
docker-compose -f backend/docker-compose.dao-service.yml down
```

### Full Build and Test Pipeline

Run the complete pipeline including Docker build and integration tests:

```bash
bash scripts/build_and_test.sh
```

This script:
1. Runs unit tests (no database)
2. Builds the Docker image
3. Deploys the container
4. Runs integration tests against the containerized service
5. Generates a test report

### Writing Your Own Tests

#### Integration Test Pattern (HTTP)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_retrieve_task(client: AsyncClient):
    """Test the full task lifecycle via HTTP."""
    
    # Create prerequisites
    user_resp = await client.post("/api/v1/users/", json={
        "name": "Test User",
        "email": "test@example.com",
    })
    user_id = user_resp.json()["id"]
    
    goal_resp = await client.post("/api/v1/goals/", json={
        "user_id": user_id,
        "title": "Test Goal",
    })
    goal_id = goal_resp.json()["id"]
    
    # Create task
    task_resp = await client.post("/api/v1/tasks/", json={
        "user_id": user_id,
        "goal_id": goal_id,
        "title": "Test Task",
        "state": "scheduled",
    })
    assert task_resp.status_code == 201
    task = task_resp.json()
    
    # Verify retrieval
    get_resp = await client.get(f"/api/v1/tasks/{task['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Test Task"
```

#### Unit Test Pattern (Direct API)

```python
import pytest
from dao_service.schemas.task import TaskCreateDTO, TaskDTO
from dao_service.schemas.enums import TaskState, TaskPriority
from uuid import uuid4

def test_task_create_dto_validation():
    """Test DTO validation without database."""
    
    # Valid DTO
    dto = TaskCreateDTO(
        user_id=uuid4(),
        goal_id=uuid4(),
        title="Valid task",
        state=TaskState.SCHEDULED,
        priority=TaskPriority.STANDARD,
    )
    assert dto.title == "Valid task"
    
    # Invalid: empty title
    with pytest.raises(ValueError):
        TaskCreateDTO(
            user_id=uuid4(),
            goal_id=uuid4(),
            title="",  # min_length=1 violation
        )
```

### Test Configuration

The test suite uses these fixtures from `backend/tests/conftest.py`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `test_engine` | session | Async SQLAlchemy engine |
| `setup_database` | session | Truncates tables before tests |
| `db_session` | function | Fresh session per test |
| `client` | function | Async HTTP client with auth bypass |

### Test Data Factories

Use the factory functions for consistent test data:

```python
from tests.conftest import make_user_data, make_goal_data, make_task_data

# Generate test data with defaults
user_data = make_user_data()
goal_data = make_goal_data(user_id)
task_data = make_task_data(user_id, goal_id, state="completed")
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Connection refused` on port 8000 | DAO Service not running | Start with `make dev` or Docker |
| `Connection refused` on port 54322 | Supabase not running | Run `supabase start` |
| `403 Forbidden` | Invalid or missing API key | Check `X-Flux-Service-Key` header |
| `404 Not Found` | Entity doesn't exist | Verify UUID is correct |
| `422 Unprocessable Entity` | FK constraint violation | Check referenced IDs exist |
| Tests hang | Event loop binding issue | Use `pytest-asyncio` correctly |
| `asyncpg` build fails | Missing system libs | Use binary wheel: `pip install --only-binary=:all: asyncpg` |

### Checking Service Health

```bash
# Liveness (process running)
curl http://localhost:8000/health

# Readiness (database connected)
curl http://localhost:8000/ready
```

### Viewing Logs

```bash
# Docker logs
docker logs flux-dao-service -f

# Local development (uvicorn output in terminal)
make dev
```

### Database Connection Issues

Verify the `DATABASE_URL` environment variable:

```bash
# Local development
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

# Docker (uses host.docker.internal)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:54322/postgres
```

### Resetting Test Database

```bash
# Truncate all data
supabase db reset

# Or manually truncate
psql "postgresql://postgres:postgres@localhost:54322/postgres" -c "TRUNCATE users CASCADE;"
```

---

## Additional Resources

- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Design Document**: `docs/flux_data_access_layer_design.md`
- **Test Examples**: `backend/tests/integration/test_api/`

---

**Document End**

# Flux Data Access Layer Design

**Document Version**: 1.3
**Date**: 2026-02-23
**Status**: Implementation Complete

---

## Executive Summary

This document outlines the architecture for Flux's **Data Access Microservice** - a standalone REST API service that provides framework-agnostic, scalable data persistence and retrieval for the Flux AI agents (Goal Planner, Scheduler, Observer).

**Key Features**:
- Framework-independent design using `DatabaseSession` protocol
- Strict layer separation (ORM, DTO, DAO, Service, API)
- Data validation only (NO business logic in this service)
- Enterprise naming conventions with `dao_` prefix
- Full ACID transaction support
- OpenAPI 3.0 compliant REST API

---

## Table of Contents

1. [Key Design Decisions](#key-design-decisions)
2. [Architecture Scope](#architecture-scope)
3. [API Design](#api-design)
4. [Interaction Flows](#interaction-flows)
5. [Technology Stack](#technology-stack)
6. [Directory Structure](#directory-structure)
7. [Layer Architecture](#layer-architecture)
8. [Framework Pluggability](#framework-pluggability)
9. [ACID Transactions](#acid-transactions)
10. [Implementation Phases](#implementation-phases)
11. [Verification Strategy](#verification-strategy)

---

## Key Design Decisions

### 1. Framework Independence via DatabaseSession Protocol

**Problem**: Using SQLAlchemy's `AsyncSession` directly couples service/DAO layers to SQLAlchemy, making ORM migration impossible without widespread code changes.

**Solution**: Created `DatabaseSession` protocol that defines the async context manager and transaction methods any ORM session must implement.

**Benefits**:
- Services and DAOs use generic `DatabaseSession` type
- Switching from SQLAlchemy to Tortoise ORM requires ZERO service layer changes
- ORM-specific code limited to DAO implementations only

**Example**:
```python
# dao_service/core/database.py
class DatabaseSession(Protocol):
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...

# Service layer uses protocol (framework-agnostic)
async def create_task(db: DatabaseSession, task_data: TaskCreateDTO):
    # Works with SQLAlchemy, Tortoise, or any future ORM
    ...
```

---

### 2. Service Layer Scope: Data Validation Only

**Problem**: Original design included business logic (authorization, workflow rules) in the service layer, violating single responsibility and microservice boundaries.

**Correction**: Service layer handles **ONLY**:
- Data format validation (via Pydantic DTOs)
- Technical limits (pagination caps)
- Optional FK existence checks

**Business Logic Excluded** (belongs in Goal Planner/Scheduler/Observer microservices):
- User authorization (does user own this goal?)
- Workflow decisions (should this task be created now?)
- Pattern analysis (what does drift rate tell us?)

**Example**:
```python
# ✅ CORRECT - Data validation only
class DaoTaskService:
    async def create_task(self, db: DatabaseSession, task_data: TaskCreateDTO):
        # DTO has already validated field formats (status, trigger_type, etc.)
        # No business logic here — just persist
        return await self.task_dao.create(db, task_data)

# ❌ WRONG - Business logic (belongs in Goal Planner service)
async def create_task(self, db: DatabaseSession, task_data: TaskCreateDTO):
    # ❌ Authorization check - NOT data validation
    if goal.user_id != task_data.user_id:
        raise PermissionError("Goal does not belong to user")

    # ❌ Workflow decision - NOT data validation
    if user.task_count > user.quota:
        raise BusinessRuleError("User exceeded task quota")
```

---

### 3. Enterprise Naming Conventions

**Pattern**: Prefix all data access layer files and classes with `dao_`

**Rationale**:
- Clear distinction between business services (in Goal Planner/Scheduler) and data access services
- Standard convention in enterprise Python projects
- Prevents naming conflicts (e.g., `task_service.py` in multiple microservices)

**Naming Table**:
| Type | Example File | Example Class |
|------|-------------|---------------|
| Service | `dao_task_service.py` | `DaoTaskService` |
| DAO Implementation | `dao_task.py` | `DaoTask` |
| DAO Protocol | `dao_protocols.py` | `TaskDAOProtocol` |
| Factory | `dao_sqlalchemy_factory.py` | `DaoSqlalchemyFactory` |
| Unit of Work | `dao_unit_of_work.py` | `DaoUnitOfWork` |

---

## Architecture Scope

### In Scope: Data Access Microservice

This service provides REST API endpoints for:
- **CRUD operations** on all entities (users, goals, tasks, conversations, patterns, notification_log)
- **Custom queries** for Scheduler (tasks by time range, bulk status updates)
- **Aggregations** for Observer (task statistics, pattern data)
- **Transactional operations** via Unit of Work pattern

**Technology**: FastAPI → Service Layer (data validation) → DAO → ORM → PostgreSQL

---

### Out of Scope: Business Logic Microservices

The following will be **separate microservices** calling this Data Access API:

1. **Goal Planner Service** (separate codebase):
   - User intent parsing
   - Goal decomposition into tasks
   - Authorization (does user own this goal?)
   - Calls Data Access API via HTTP for persistence

2. **Scheduler Service** (separate codebase):
   - Google Calendar synchronization
   - Drift detection logic
   - Rescheduling algorithms
   - Calls Data Access API via HTTP for task retrieval/updates

3. **Observer Service** (separate codebase):
   - Pattern analysis algorithms
   - User behavior modeling
   - Recommendation generation
   - Calls Data Access API via HTTP for historical data

---

## API Design

### Complete Endpoint Inventory

#### User Endpoints (`/api/v1/users`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List users with pagination | All | `PaginatedResponse[UserDTO]` |
| GET | `/{user_id}` | Get single user | All | `UserDTO` |
| POST | `/` | Create user | Goal Planner | `UserDTO` |
| PATCH | `/{user_id}` | Update user | Goal Planner | `UserDTO` |
| DELETE | `/{user_id}` | Delete user (cascade) | Goal Planner | `204 No Content` |

#### Goal Endpoints (`/api/v1/goals`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List goals with pagination | All | `PaginatedResponse[GoalDTO]` |
| GET | `/{goal_id}` | Get single goal | All | `GoalDTO` |
| POST | `/` | Create goal | Goal Planner | `GoalDTO` |
| PATCH | `/{goal_id}` | Update goal | Goal Planner | `GoalDTO` |
| DELETE | `/{goal_id}` | Delete goal (cascade) | Goal Planner | `204 No Content` |

**Goal statuses**: `active`, `completed`, `abandoned`, `pipeline`

#### Task Endpoints (`/api/v1/tasks`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List tasks with pagination | All | `PaginatedResponse[TaskDTO]` |
| GET | `/{task_id}` | Get single task | All | `TaskDTO` |
| POST | `/` | Create task | Goal Planner, Scheduler | `TaskDTO` |
| PATCH | `/{task_id}` | Update task | Goal Planner, Scheduler | `TaskDTO` |
| DELETE | `/{task_id}` | Delete task | Goal Planner | `204 No Content` |
| GET | `/by-timerange` | Get tasks in time window | Scheduler | `List[TaskDTO]` |
| POST | `/bulk-update-state` | Bulk status updates | Scheduler | `BulkUpdateResponse` |
| GET | `/statistics` | Task completion stats | Observer | `TaskStatisticsDTO` |

**Task statuses**: `pending`, `done`, `missed`, `rescheduled`, `cancelled`
**Trigger types**: `time`, `location`

#### Conversation Endpoints (`/api/v1/conversations`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List conversations with pagination | All | `PaginatedResponse[ConversationDTO]` |
| GET | `/{conversation_id}` | Get single conversation | All | `ConversationDTO` |
| POST | `/` | Create conversation | Goal Planner, Conv Agent | `ConversationDTO` |
| PATCH | `/{conversation_id}` | Update conversation | Goal Planner | `ConversationDTO` |
| PATCH | `/{conversation_id}/voice` | Update voice-specific fields | Conv Agent | `ConversationDTO` |

**Context types**: `goal`, `task`, `onboarding`, `reschedule`, `voice`

**Voice columns** (added for conv_agent support):
- `voice_session_id` (String, nullable) -- unique voice session identifier
- `extracted_intent` (String, nullable) -- detected intent (GOAL, NEW_TASK, RESCHEDULE_TASK)
- `intent_payload` (JSONB, nullable) -- raw intent parameters
- `linked_goal_id` (UUID FK, nullable) -- goal created during session
- `linked_task_id` (UUID FK, nullable) -- task created/rescheduled during session
- `ended_at` (Timestamp, nullable) -- session end time
- `duration_seconds` (Integer, nullable) -- session duration

#### Message Endpoints (`/api/v1/messages`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| POST | `/` | Create message | Conv Agent | `MessageDTO` |
| GET | `/` | List messages by conversation_id | Conv Agent | `List[MessageDTO]` |
| GET | `/{message_id}` | Get single message | Conv Agent | `MessageDTO` |
| DELETE | `/{message_id}` | Delete message | Conv Agent | `204 No Content` |

**Roles**: `user`, `assistant`, `system`, `function`
**Input modalities**: `voice`, `text`

> **Note**: The conv_agent routes all DB access through this service via HTTP (see `ConvAgentDaoClient`).

#### Pattern Endpoints (`/api/v1/patterns`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List patterns with pagination | Observer | `PaginatedResponse[PatternDTO]` |
| GET | `/{pattern_id}` | Get single pattern | Observer | `PatternDTO` |
| POST | `/` | Record pattern | Observer | `PatternDTO` |
| PATCH | `/{pattern_id}` | Update pattern | Observer | `PatternDTO` |
| DELETE | `/{pattern_id}` | Delete pattern | Observer | `204 No Content` |

#### Notification Log Endpoints (`/api/v1/notification-log`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List log entries | Scheduler | `PaginatedResponse[NotificationLogDTO]` |
| GET | `/{id}` | Get log entry | Scheduler | `NotificationLogDTO` |
| POST | `/` | Record notification | Scheduler | `NotificationLogDTO` |
| PATCH | `/{id}` | Update log entry | Scheduler | `NotificationLogDTO` |
| DELETE | `/{id}` | Delete log entry | Scheduler | `204 No Content` |

**Channels**: `push`, `whatsapp`, `call`

#### Operational Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness check (DB connection) |

---

### Inter-Service Authentication

The current implementation does not enforce API-key authentication on endpoints — all callers have open access on the internal network. A `verify_service_key` dependency placeholder exists in `api/deps.py` and can be activated by setting `SERVICE_API_KEYS` in the environment when inter-service authentication is required.

---

### Error Response Format

All error responses follow a consistent structure:

```python
class ErrorDetail(BaseModel):
    type: str       # Error category URI
    title: str      # Human-readable summary
    status: int     # HTTP status code
    detail: str     # Specific error explanation
    instance: str   # Request path for tracing
```

**HTTP Status Code Matrix**:

| Code | When Used | Example |
|------|-----------|---------|
| 200 OK | Successful GET/PATCH | Task retrieved |
| 201 Created | Successful POST | Task created |
| 204 No Content | Successful DELETE | Task deleted |
| 400 Bad Request | Malformed JSON | Invalid UUID format |
| 404 Not Found | Entity doesn't exist | Task ID not found |
| 409 Conflict | Unique constraint violation | Duplicate `langgraph_thread_id` |
| 422 Unprocessable Entity | Validation failure | Invalid enum value |
| 500 Internal Server Error | Database failure | Connection timeout |

---

### Pagination Response Wrapper

All list endpoints return a consistent pagination envelope:

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
```

---

### Additional DTOs for Specialized Endpoints

```python
class BulkUpdateStateRequest(BaseModel):
    task_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    new_status: str  # one of: pending, done, missed, rescheduled, cancelled

class BulkUpdateResponse(BaseModel):
    updated_count: int

class TaskStatisticsDTO(BaseModel):
    user_id: UUID
    total_tasks: int
    by_status: Dict[str, int]
    completion_rate: float
```

---

## Interaction Flows

### Flow 1: Goal Creation with Tasks

The Goal Planner service decomposes a user's goal into tasks, then persists them via the Unit of Work pattern.

```mermaid
sequenceDiagram
    participant GP as Goal Planner Service
    participant API as Data Access API
    participant SVC as DaoGoalService
    participant UOW as DaoUnitOfWork
    participant DG as DaoGoal
    participant DT as DaoTask
    participant DB as PostgreSQL

    GP->>+API: POST /api/v1/goals/<br/>{user_id, title, class_tags, target_weeks}
    API->>+SVC: create_goal(data)

    SVC->>+UOW: Begin transaction

    UOW->>+DG: create(db, GoalCreateDTO)
    DG->>+DB: INSERT INTO goals
    DB-->>-DG: goal_id
    DG-->>-UOW: GoalDTO

    loop For each task
        UOW->>+DT: create(db, TaskCreateDTO)
        DT->>+DB: INSERT INTO tasks
        DB-->>-DT: task_id
        DT-->>-UOW: TaskDTO
    end

    UOW->>DB: COMMIT
    UOW-->>-SVC: GoalDTO + List[TaskDTO]
    SVC-->>-API: GoalDTO
    API-->>-GP: 201 Created
```

### Flow 2: Scheduler — Standalone Task Creation

The Scheduler creates a rescheduled task for a missed one.

```mermaid
sequenceDiagram
    participant SC as Scheduler Service
    participant API as Data Access API
    participant TSVC as DaoTaskService
    participant DT as DaoTask
    participant DB as PostgreSQL

    Note over SC: Missed task detected — create rescheduled replacement

    SC->>+API: POST /api/v1/tasks/<br/>{user_id, goal_id, title, status: "pending", trigger_type: "time"}
    API->>+TSVC: create_task(db, TaskCreateDTO)
    TSVC->>+DT: create(db, TaskCreateDTO)
    DT->>+DB: INSERT INTO tasks
    DB-->>-DT: task_id
    DT-->>-TSVC: TaskDTO
    TSVC-->>-API: TaskDTO
    API-->>-SC: 201 Created — TaskDTO
```

### Flow 3: Scheduler — Time Range Query & Bulk Status Update

The Scheduler periodically queries tasks in a time window, runs drift detection logic, then bulk-updates missed task statuses.

```mermaid
sequenceDiagram
    participant SC as Scheduler Service
    participant API as Data Access API
    participant SVC as DaoTaskService
    participant DAO as DaoTask
    participant DB as PostgreSQL

    SC->>+API: GET /api/v1/tasks/by-timerange<br/>?user_id=X&start_at=T1&end_at=T2
    API->>+SVC: get_tasks_for_scheduling(user_id, T1, T2)
    SVC->>+DAO: get_tasks_by_user_and_timerange(...)
    DAO->>+DB: SELECT FROM tasks<br/>WHERE user_id=X AND scheduled_at BETWEEN T1,T2
    DB-->>-DAO: [task rows]
    DAO-->>-SVC: List[TaskDTO]
    SVC-->>-API: List[TaskDTO]
    API-->>-SC: 200 OK — List[TaskDTO]

    Note over SC: Missed-task detection logic runs<br/>(business logic in Scheduler)

    SC->>+API: POST /api/v1/tasks/bulk-update-state<br/>{task_ids: [id1, id2], new_status: "missed"}
    API->>+SVC: bulk_update_status([id1, id2], "missed")
    SVC->>+DAO: bulk_update_status([id1, id2], "missed")
    DAO->>+DB: UPDATE tasks SET status='missed'<br/>WHERE id IN (id1, id2)
    DB-->>-DAO: 2 rows affected
    DAO-->>-SVC: 2
    SVC-->>-API: BulkUpdateResponse
    API-->>-SC: 200 OK — {updated_count: 2}
```

### Flow 4: Observer — Task Statistics for Pattern Analysis

The Observer queries aggregated task statistics to detect user behavior patterns (e.g., recurring drift on Monday mornings).

```mermaid
sequenceDiagram
    participant OB as Observer Service
    participant API as Data Access API
    participant SVC as DaoTaskService
    participant DAO as DaoTask
    participant DB as PostgreSQL

    OB->>+API: GET /api/v1/tasks/statistics<br/>?user_id=X&start_date=D1&end_date=D2
    API->>+SVC: get_task_statistics(user_id, D1, D2)
    SVC->>+DAO: get_task_statistics(user_id, D1, D2)
    DAO->>+DB: SELECT status, COUNT(*) FROM tasks<br/>WHERE user_id=X AND created_at BETWEEN D1,D2<br/>GROUP BY status
    DB-->>-DAO: {pending:15, done:42, missed:8, rescheduled:3, cancelled:1}
    DAO-->>-SVC: TaskStatisticsDTO
    SVC-->>-API: TaskStatisticsDTO
    API-->>-OB: 200 OK — TaskStatisticsDTO

    Note over OB: Pattern analysis runs<br/>(business logic in Observer)
```

### Flow 5: Internal Layer Flow — Single CRUD Request

Shows how a request traverses all internal layers of the Data Access service.

```mermaid
sequenceDiagram
    participant Client as Calling Service
    participant Router as FastAPI Router
    participant Deps as Dependencies
    participant Service as DaoTaskService
    participant DAO as DaoTask (impl/sqlalchemy)
    participant ORM as SQLAlchemy Session
    participant DB as PostgreSQL

    Client->>+Router: POST /api/v1/tasks
    Router->>+Deps: get_db()
    Deps->>+ORM: AsyncSessionLocal()
    ORM-->>-Deps: session (as DatabaseSession)
    Deps-->>-Router: db

    Router->>+Deps: get_task_service()
    Deps-->>-Router: DaoTaskService

    Router->>+Service: create_task(db, TaskCreateDTO)

    Service->>+DAO: task_dao.create(db, TaskCreateDTO)
    DAO->>DAO: Cast db → SQLAlchemyAsyncSession
    DAO->>+ORM: session.add(Task), flush(), refresh()
    ORM->>+DB: INSERT INTO tasks
    DB-->>-ORM: task row
    ORM-->>-DAO: Task object
    DAO-->>-Service: TaskDTO

    Service-->>-Router: TaskDTO

    Router->>+ORM: commit()
    ORM->>+DB: COMMIT
    DB-->>-ORM: ok
    ORM-->>-Router: ok

    Router-->>-Client: 201 Created — TaskDTO
```

---

## Technology Stack

### Core Dependencies

```python
# backend/dao_service/requirements.txt
fastapi==0.115.6           # Async web framework with OpenAPI support
uvicorn[standard]==0.34.0  # ASGI server
sqlalchemy[asyncio]==2.0.38  # Modern ORM with async/await
asyncpg==0.31.0            # Fastest async PostgreSQL driver
pydantic==2.10.4           # Fast validation and serialization
pydantic-settings==2.7.1   # Environment variable management
python-dotenv==1.0.1       # .env file loading
python-json-logger==2.0.7  # Structured logging
```

### Design Patterns

- **Protocol-based DAO interfaces** (`typing.Protocol`) for framework abstraction
- **Factory pattern** for DAO creation with framework selection
- **Unit of Work pattern** for ACID transactions
- **Repository pattern** for complex multi-DAO operations
- **Async-first architecture** for non-blocking I/O

---

## Directory Structure

```
backend/
├── dao_service/                          # DAO microservice root
│   ├── __init__.py
│   ├── main.py                          # FastAPI app + global exception handlers
│   ├── config.py                        # Pydantic Settings
│   │
│   ├── core/                            # Core infrastructure
│   │   ├── __init__.py
│   │   ├── database.py                  # DatabaseSession protocol, engine, session factory
│   │   ├── exceptions.py                # Custom exceptions
│   │   └── logging.py                   # Structured logging
│   │
│   ├── models/                          # SQLAlchemy ORM layer
│   │   ├── __init__.py
│   │   ├── base.py                      # Declarative base, mixins
│   │   ├── user_model.py
│   │   ├── goal_model.py
│   │   ├── task_model.py
│   │   ├── conversation_model.py
│   │   ├── message_model.py
│   │   ├── pattern_model.py
│   │   └── notification_log_model.py
│   │
│   ├── schemas/                         # Pydantic DTO layer
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── pagination.py                # PaginatedResponse generic wrapper
│   │   ├── error.py                     # ErrorDetail response schema
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── task.py                      # TaskDTO, BulkUpdateStateRequest, TaskStatisticsDTO
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── pattern.py
│   │   └── notification_log.py
│   │
│   ├── dao/                             # Data Access Object layer
│   │   ├── __init__.py
│   │   ├── dao_protocols.py             # Abstract DAO interfaces (Protocol-based)
│   │   ├── dao_factory.py               # DaoFactoryProtocol
│   │   ├── dao_registry.py              # Framework selection logic
│   │   │
│   │   ├── factories/                   # Concrete factory implementations
│   │   │   ├── __init__.py
│   │   │   └── dao_sqlalchemy_factory.py
│   │   │
│   │   └── impl/                        # DAO implementations by framework
│   │       └── sqlalchemy/
│   │           ├── __init__.py
│   │           ├── dao_user.py
│   │           ├── dao_goal.py
│   │           ├── dao_task.py          # Extended queries (time range, bulk update, statistics)
│   │           ├── dao_conversation.py
│   │           ├── dao_message.py
│   │           ├── dao_pattern.py
│   │           └── dao_notification_log.py
│   │
│   ├── repositories/                    # Repository pattern
│   │   ├── __init__.py
│   │   └── dao_unit_of_work.py          # DaoUnitOfWork class
│   │
│   ├── services/                        # Data validation services
│   │   ├── __init__.py
│   │   ├── dao_user_service.py
│   │   ├── dao_goal_service.py
│   │   ├── dao_task_service.py
│   │   ├── dao_conversation_service.py
│   │   ├── dao_message_service.py
│   │   ├── dao_pattern_service.py
│   │   └── dao_notification_log_service.py
│   │
│   ├── api/                             # FastAPI routes
│   │   ├── __init__.py
│   │   ├── deps.py                      # Dependencies (get_db, service factories)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── users_api.py
│   │       ├── goals_api.py
│   │       ├── tasks_api.py
│   │       ├── conversations_api.py
│   │       ├── messages_api.py
│   │       ├── patterns_api.py
│   │       └── notification_log_api.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                  # PostgreSQL fixtures + data factories
│   │   ├── unit/
│   │   │   ├── test_dao/                # DAO unit tests (mock DB session)
│   │   │   └── test_services/           # Service unit tests (mock DAO)
│   │   └── integration/
│   │       └── test_api/                # API endpoint tests (needs Supabase)
│   │
│   ├── scripts/
│   │   ├── build_and_test.sh            # Full pipeline: Docker build + all tests + report
│   │   ├── run_tests.sh                 # Run unit/integration/all tests with coverage
│   │   └── setup_dao.sh                 # Environment setup & dependency install
│   │
│   ├── requirements.txt                 # Production dependencies
│   └── requirements-dev.txt             # Development/test dependencies
│
├── Dockerfile                           # Docker image
├── .dockerignore
├── Makefile
├── pytest.ini
└── pyproject.toml
```

---

## Layer Architecture

### Layer 1: Configuration & Database Core

**Purpose**: Framework-agnostic database session management.

**DatabaseSession Protocol** (enables ORM switching):
```python
# dao_service/core/database.py
from typing import Protocol

class DatabaseSession(Protocol):
    """
    Framework-agnostic database session protocol.

    Any ORM framework's session type can satisfy this protocol.
    CRITICAL: Use this instead of AsyncSession for framework independence.
    """
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...
```

**SQLAlchemy Implementation**:
```python
# dao_service/core/database.py (continued)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,           # Base pool size
    max_overflow=10,        # Additional connections when needed
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle after 1 hour
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=SQLAlchemyAsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[DatabaseSession, None]:
    """Returns SQLAlchemy session typed as generic DatabaseSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session  # Type: DatabaseSession, actual: AsyncSession
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

#### DatabaseSession Protocol — Design Rationale

The `DatabaseSession` protocol is **intentionally thin** — it only defines transaction lifecycle methods (`commit`, `rollback`, `close`), not query execution methods. This is deliberate:

1. **Query APIs are framework-specific** — SQLAlchemy uses `session.execute(select(...))`, Tortoise uses `Model.filter(...)`, Django ORM uses `Model.objects.filter(...)`. There is no useful common denominator for query execution.

2. **The real abstraction boundary is the DAO Protocol layer** — Services depend on `TaskDAOProtocol`, not on database session internals. DAO implementations handle framework-specific queries behind the protocol interface.

3. **DAO implementations are explicitly framework-specific** — Files in `impl/sqlalchemy/` are expected to cast `db` to `SQLAlchemyAsyncSession`. This is correct by design — these files exist specifically for SQLAlchemy-specific code.

#### Framework Migration Checklist

When switching from SQLAlchemy to another ORM (e.g., Tortoise):

| Layer | Changes Required? | Details |
|-------|:-:|---------|
| ORM Models (`dao_service/models/`) | **Yes** | Rewrite for target ORM |
| DAO Implementations (`dao_service/dao/impl/`) | **Yes** | New `impl/tortoise/` directory |
| Database Connection (`dao_service/core/database.py`) | **Yes** | Target ORM's connection setup |
| DAO Factory (`dao_service/dao/factories/`) | **Yes** | New `dao_tortoise_factory.py` |
| DAO Registry (`dao_service/dao/dao_registry.py`) | **Minimal** | Register new factory |
| DAO Protocols (`dao_service/dao/dao_protocols.py`) | **No** | Unchanged |
| DTOs / Schemas (`dao_service/schemas/`) | **No** | Unchanged |
| Services (`dao_service/services/`) | **No** | Unchanged |
| API Layer (`dao_service/api/`) | **No** | Unchanged |

The service layer, API layer, and DTOs require **zero changes** — that is the key achievement of this architecture.

---

### Layer 2: ORM Models (SQLAlchemy)

**Purpose**: Map database tables to Python objects.

**Task Model Example**:
```python
# dao_service/models/task_model.py
from sqlalchemy.orm import Mapped, relationship

class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[UUID]           # FK → users.id CASCADE
    goal_id: Mapped[Optional[UUID]] # FK → goals.id CASCADE (nullable)

    title: Mapped[str]
    description: Mapped[Optional[str]]
    status: Mapped[str]             # pending | done | missed | rescheduled | cancelled
    scheduled_at: Mapped[Optional[datetime]]
    duration_minutes: Mapped[Optional[int]]
    trigger_type: Mapped[str]       # time | location
    location_trigger: Mapped[Optional[str]]
    recurrence_rule: Mapped[Optional[str]]
    completed_at: Mapped[Optional[datetime]]

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    goal: Mapped[Optional["Goal"]] = relationship(back_populates="tasks")
    notification_logs: Mapped[List["NotificationLog"]] = relationship(back_populates="task")
```

---

### Layer 3: DTOs (Pydantic Schemas)

**Purpose**: API contracts with validation, separate from database structure.

**Task DTO Pattern**:
```python
# dao_service/schemas/task.py

TASK_STATUS_VALUES = {"pending", "done", "missed", "rescheduled", "cancelled"}
TRIGGER_TYPE_VALUES = {"time", "location"}

class TaskBase(BaseSchema):
    """Shared attributes."""
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "pending"          # validated against TASK_STATUS_VALUES
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    trigger_type: str = "time"       # validated against TRIGGER_TYPE_VALUES
    location_trigger: Optional[str] = None
    recurrence_rule: Optional[str] = None
    completed_at: Optional[datetime] = None

class TaskCreateDTO(TaskBase):
    """For creation requests."""
    user_id: UUID
    goal_id: Optional[UUID] = None

class TaskUpdateDTO(BaseSchema):
    """For updates — all fields optional."""
    title: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    goal_id: Optional[UUID] = None

class TaskDTO(TaskBase):
    """Complete response schema."""
    id: UUID
    user_id: UUID
    goal_id: Optional[UUID] = None
    created_at: datetime
```

---

### Layer 4: DAO Protocols (Framework-Agnostic Interfaces)

**Purpose**: Define abstract contracts using DatabaseSession protocol.

**Task DAO Protocol**:
```python
# dao_service/dao/dao_protocols.py
from typing import Protocol, List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from dao_service.core.database import DatabaseSession
from dao_service.schemas.task import TaskDTO, TaskCreateDTO, TaskUpdateDTO

class TaskDAOProtocol(Protocol):
    """Framework-agnostic task DAO interface."""

    # Standard CRUD
    async def create(self, db: DatabaseSession, obj_in: TaskCreateDTO) -> TaskDTO: ...
    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[TaskDTO]: ...
    async def get_multi(self, db: DatabaseSession, skip: int, limit: int) -> List[TaskDTO]: ...
    async def update(self, db: DatabaseSession, id: UUID, obj_in: TaskUpdateDTO) -> Optional[TaskDTO]: ...
    async def delete(self, db: DatabaseSession, id: UUID) -> bool: ...

    # Custom methods for Scheduler microservice
    async def get_tasks_by_user_and_timerange(
        self, db: DatabaseSession, user_id: UUID, start_at: datetime, end_at: datetime
    ) -> List[TaskDTO]: ...

    async def bulk_update_status(
        self, db: DatabaseSession, task_ids: List[UUID], new_status: str
    ) -> int: ...

    # Custom methods for Observer microservice
    async def get_task_statistics(
        self, db: DatabaseSession, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]: ...
```

---

### Layer 5: DAO Implementations

**Purpose**: Concrete SQLAlchemy implementations with ORM-specific code.

**DaoTask Implementation**:
```python
# dao_service/dao/impl/sqlalchemy/dao_task.py
from sqlalchemy import select, update as sql_update, func
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession
from dao_service.core.database import DatabaseSession
from dao_service.models.task import Task
from dao_service.schemas.task import TaskDTO, TaskCreateDTO, TaskUpdateDTO

class DaoTask:
    """SQLAlchemy implementation of TaskDAOProtocol."""

    async def create(self, db: DatabaseSession, obj_in: TaskCreateDTO) -> TaskDTO:
        # Cast to SQLAlchemy session for ORM operations
        session: SQLAlchemyAsyncSession = db

        db_obj = Task(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return TaskDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[TaskDTO]:
        session: SQLAlchemyAsyncSession = db

        stmt = select(Task).where(Task.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return TaskDTO.model_validate(db_obj) if db_obj else None

    async def get_tasks_by_user_and_timerange(
        self, db: DatabaseSession, user_id: UUID, start_at: datetime, end_at: datetime
    ) -> List[TaskDTO]:
        session: SQLAlchemyAsyncSession = db

        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.scheduled_at >= start_at)
            .where(Task.scheduled_at <= end_at)
            .order_by(Task.scheduled_at)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        return [TaskDTO.model_validate(t) for t in tasks]

    async def get_task_statistics(
        self, db: DatabaseSession, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        session: SQLAlchemyAsyncSession = db

        stmt = (
            select(
                Task.status,
                func.count(Task.id).label("count"),
            )
            .where(Task.user_id == user_id)
            .where(Task.created_at >= start_date)
            .where(Task.created_at <= end_date)
            .group_by(Task.status)
        )
        result = await session.execute(stmt)
        stats = {row.status: row.count for row in result}
        return stats
```

---

### Layer 6: Service Layer (Data Validation Only)

**Purpose**: Handle data validation and referential integrity - NO business logic.

**DaoTaskService Example**:
```python
# dao_service/services/dao_task_service.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from dao_service.core.database import DatabaseSession
from dao_service.schemas.task import TaskDTO, TaskCreateDTO, TaskUpdateDTO
from dao_service.dao.dao_registry import get_task_dao
from dao_service.dao.dao_protocols import TaskDAOProtocol

class DaoTaskService:
    """
    Data validation service for tasks.

    Responsibilities:
    - Data format validation (Pydantic handles this)
    - Technical limits (pagination cap)
    - NO business logic (that belongs in Goal Planner/Scheduler/Observer)
    """

    def __init__(self):
        self.task_dao: TaskDAOProtocol = get_task_dao()

    async def get_tasks(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[TaskDTO]:
        """Retrieve tasks with pagination cap."""
        if limit > 100:
            limit = 100
        return await self.task_dao.get_multi(db, skip=skip, limit=limit)

    async def create_task(
        self, db: DatabaseSession, task_data: TaskCreateDTO
    ) -> TaskDTO:
        """
        Create task — data format validation only.

        Business Logic NOT Here:
        - ❌ Does goal belong to user? (Goal Planner service checks)
        - ❌ Should task be created now? (Goal Planner service decides)
        """
        return await self.task_dao.create(db, task_data)

    async def get_tasks_for_scheduling(
        self, db: DatabaseSession, user_id: UUID, start_at: datetime, end_at: datetime
    ) -> List[TaskDTO]:
        """
        Data retrieval for Scheduler microservice.
        NO scheduling logic here — just query execution.
        """
        return await self.task_dao.get_tasks_by_user_and_timerange(
            db, user_id, start_at, end_at
        )
```

---

### Layer 7: API Layer (FastAPI Endpoints)

**Purpose**: Expose services via HTTP with OpenAPI documentation.

Services are injected via FastAPI's `Depends()` rather than instantiated per-request. The `verify_service_key` dependency authenticates all inter-service calls.

**Representative Endpoint Example** (same pattern applies to all endpoints):
```python
# dao_service/api/v1/tasks_api.py
from fastapi import APIRouter, Depends, HTTPException, status
from dao_service.core.database import DatabaseSession
from dao_service.api.deps import get_db
from dao_service.schemas.task import TaskDTO, TaskCreateDTO
from dao_service.services.dao_task_service import DaoTaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

def get_task_service() -> DaoTaskService:
    return DaoTaskService()

@router.post("/", response_model=TaskDTO, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
):
    """Create a new task."""
    try:
        return await service.create_task(db, task_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

All endpoints in the [Complete Endpoint Inventory](#complete-endpoint-inventory) follow this same dependency injection pattern.

---

## Framework Pluggability

### Factory Pattern for ORM Switching

**1. Abstract Factory Protocol**:
```python
# dao_service/dao/dao_factory.py
class DaoFactoryProtocol(Protocol):
    def create_user_dao(self) -> UserDAOProtocol: ...
    def create_goal_dao(self) -> GoalDAOProtocol: ...
    def create_task_dao(self) -> TaskDAOProtocol: ...
    def create_conversation_dao(self) -> ConversationDAOProtocol: ...
    def create_pattern_dao(self) -> PatternDAOProtocol: ...
    def create_notification_log_dao(self) -> NotificationLogDAOProtocol: ...
```

**2. SQLAlchemy Factory**:
```python
# dao_service/dao/factories/dao_sqlalchemy_factory.py
class DaoSqlalchemyFactory:
    def create_task_dao(self) -> DaoTask:
        return DaoTask()  # SQLAlchemy implementation
```

**3. Registry with Config-Based Selection**:
```python
# dao_service/dao/dao_registry.py
from dao_service.config import settings, ORMFramework

_FACTORY_REGISTRY: dict[ORMFramework, type[DaoFactoryProtocol]] = {
    ORMFramework.SQLALCHEMY: DaoSqlalchemyFactory,
    # Future: ORMFramework.TORTOISE: DaoTortoiseFactory,
}

def get_dao_factory() -> DaoFactoryProtocol:
    factory_class = _FACTORY_REGISTRY[settings.ORM_FRAMEWORK]
    return factory_class()
```

**4. Switching ORMs**:
```bash
# .env file - single line change
ORM_FRAMEWORK=tortoise  # Changed from 'sqlalchemy'
```

**Result**: ZERO changes needed in service layer, API layer, or business logic.

---

## ACID Transactions

### Atomicity: Unit of Work Pattern

```python
# dao_service/repositories/dao_unit_of_work.py
class DaoUnitOfWork:
    def __init__(self, db: DatabaseSession):
        self.db = db
        factory = get_dao_factory()
        self.users = factory.create_user_dao()
        self.goals = factory.create_goal_dao()
        self.tasks = factory.create_task_dao()
        self.conversations = factory.create_conversation_dao()
        self.patterns = factory.create_pattern_dao()
        self.notification_logs = factory.create_notification_log_dao()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()  # Exception → rollback
        else:
            await self.commit()    # Success → commit
```

**Usage** (called by Goal Planner microservice via HTTP):
```python
async with DaoUnitOfWork(db) as uow:
    goal = await uow.goals.create(db, goal_data)
    task = await uow.tasks.create(db, task_data)
    # If ANY operation fails, ALL are rolled back
```

### Consistency: DTO Validation + DB Constraints

- **Application Level**: Pydantic validates data format before DB call
- **Database Level**: PostgreSQL enforces FK constraints, NOT NULL, CHECK constraints

### Isolation: PostgreSQL Read Committed

- Default isolation level: READ COMMITTED
- Row-level locking for concurrent updates
- Connection pooling (pool_size=20, max_overflow=10)

### Durability: PostgreSQL WAL + fsync

- Write-Ahead Logging ensures changes are on disk before commit returns
- Automatic recovery on crash

---

## Implementation Phases

### Phase 1: Foundation
1. Create `dao_service/config.py` - Pydantic Settings
2. Create `dao_service/core/database.py` - DatabaseSession protocol, async engine
3. Create `dao_service/models/base.py` - Base, mixins
4. Create `dao_service/models/enums.py` - Enum classes
5. Test database connection

**Validation**: Successfully connect to Supabase local instance.

### Phase 2: ORM Models
**Prerequisites**: Phase 1 complete
6. Create all ORM models in `dao_service/models/`
7. Initialize Alembic
8. Create migration for `calendar_event_id` field
9. Apply migration

**Validation**: Verify `calendar_event_id` column exists.

### Phase 3: DTOs
**Prerequisites**: Phase 2 complete
10. Create `dao_service/schemas/base.py` and all entity schemas
11. Create `dao_service/schemas/enums.py` (Pydantic versions)
12. Write DTO validation tests in `dao_service/tests/unit/test_schemas/`

**Validation**: Test DTO validation with pytest.

### Phase 4: DAO Layer
**Prerequisites**: Phase 3 complete
13. Create `dao_service/dao/dao_protocols.py` (using DatabaseSession)
14. Create `dao_service/dao/dao_factory.py` (DaoFactoryProtocol)
15. Create `dao_service/dao/dao_registry.py`
16. Create `dao_service/dao/factories/dao_sqlalchemy_factory.py`
17. Create all DAO implementations in `dao_service/dao/impl/sqlalchemy/`
18. Write unit tests

**Validation**: DAO tests pass. Can switch frameworks via config.

### Phase 5: Unit of Work
**Prerequisites**: Phase 4 complete
19. Create `dao_service/repositories/dao_unit_of_work.py`
20. Write integration test for transactional operations in `dao_service/tests/integration/`

**Validation**: Test rollback behavior.

### Phase 6: Service Layer
**Prerequisites**: Phase 5 complete
21. Create `dao_user_service.py`, `dao_goal_service.py`, `dao_task_service.py`, etc.

**Validation**: Services handle only data validation, NO business logic.

### Phase 7: API Layer
**Prerequisites**: Phase 6 complete
22. Create `dao_service/api/deps.py` (get_db returns DatabaseSession)
23. Create all v1 endpoints in `dao_service/api/v1/`
24. Create `dao_service/main.py`

**Validation**: Test endpoints with FastAPI TestClient.

### Phase 8: Testing & Documentation
**Prerequisites**: Phase 7 complete
25. Write integration tests
26. Add docstrings
27. Create backend README

**Validation**: All tests pass. OpenAPI docs render correctly.

---

## Verification Strategy

### End-to-End Testing

1. **CRUD Operations**:
   - Create, read, update, delete tasks
   - Verify cascade deletion (delete goal → tasks deleted)

2. **Custom Queries**:
   - Retrieve tasks by time range
   - Get task statistics (aggregations)
   - Bulk update task states

3. **Framework Switching**:
   - Change `ORM_FRAMEWORK=tortoise` in .env
   - Verify service layer code unchanged
   - Verify API endpoints still work

### ACID Transaction Testing

4. **Atomicity Test**:
   - Attempt transactional operation with invalid data
   - Verify rollback: no partial state persists

5. **Consistency Test**:
   - Attempt to create task with invalid enum value
   - Verify Pydantic validation rejects before database call

6. **Isolation Test**:
   - Run 10 concurrent goal creations
   - Verify no race conditions

7. **Durability Test**:
   - Create goal
   - Simulate database restart (stop/start Supabase)
   - Verify goal still exists

---

## Development Setup and Testing Guide

### Prerequisites

Before working with the DAO service, ensure you have:

1. **Docker Desktop** — installed and running
2. **Supabase CLI** — `brew install supabase/tap/supabase`
3. **Supabase local instance** — running via `bash scripts/supabase_setup.sh`
4. **Python 3.11+** — with a project-level virtual environment activated
5. **Dependencies installed**:
   - Production: `pip install -r backend/dao_service/requirements.txt`
   - Development/testing: `pip install -r backend/dao_service/requirements-dev.txt`

### Quick Start: Running the DAO Service Locally

Use this flow to try the API interactively via Swagger UI:

1. **Verify Supabase is running:**
   ```bash
   supabase status
   ```

2. **Create `.env` in `backend/`** (if not already present):
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
   SERVICE_API_KEYS=["goal-planner-key-abc","scheduler-key-def","observer-key-ghi"]
   ```

3. **Start the development server:**
   ```bash
   cd backend && make dev
   ```

4. **Open Swagger UI:** http://localhost:8000/docs

5. **Try a basic flow via Swagger:**
   - **POST** `/api/v1/users/` — Create a user (returns user with `id`)
   - **POST** `/api/v1/goals/` — Create a goal using the user's `id`
   - **POST** `/api/v1/tasks/` — Create a task linked to the user and goal
   - **GET** `/api/v1/tasks/by-timerange` — Query tasks in a time window
   - **GET** `/api/v1/tasks/statistics` — View completion statistics

7. **Other documentation endpoints:**
   - ReDoc: http://localhost:8000/redoc
   - OpenAPI JSON spec: http://localhost:8000/openapi.json

### Running the DAO Service via Docker

The dao service is defined in the root `docker-compose.yml`. Run from the project root:

```bash
# Start the dao service (and its dependencies)
docker compose up dao

# Or start standalone in detached mode
docker compose up -d dao

# Verify it's running
curl http://localhost:8001/health

# Swagger UI
open http://localhost:8001/docs

# Stop
docker compose down dao
```

The Docker container connects to Supabase on the host via `host.docker.internal:54322`.
Within the Docker network, other services reach the dao service at `http://dao:8001`.

### Running Tests

```bash
# Unit tests only (no database needed, runs in ~0.02s)
cd backend && pytest dao_service/tests/unit/ -v

# Integration tests only (needs Supabase running)
cd backend && pytest dao_service/tests/integration/ -v

# Full DAO test suite
cd backend && pytest dao_service/tests/ -v

# Full pipeline: build → unit tests → Docker deploy → integration tests → HTML/XML report
bash backend/dao_service/scripts/build_and_test.sh

# Tests only with HTML report (no Docker build)
bash backend/dao_service/scripts/run_tests.sh
```

**Test Architecture:**
- **103 unit tests** — DAO CRUD tests (mock DB session) + service tests (mock DAO), no database required, located in `dao_service/tests/unit/`
- **49 integration tests** — Full API endpoint testing against Supabase PostgreSQL, located in `dao_service/tests/integration/`
- **Test isolation** — Tables truncated at session start; each test uses a fresh ASGI client
- **Async support** — Uses `pytest-asyncio` with session-scoped event loops
- **Test discovery** — `pytest.ini` `testpaths` covers both `tests/` (legacy) and `dao_service/tests/`

### Calling the DAO Service from Python (Other Services)

If another Flux service (Goal Planner, Scheduler, Observer) needs to call this service directly from Python, use `httpx.AsyncClient`. The integration tests demonstrate the exact pattern:

```python
# Reference: backend/dao_service/tests/integration/test_api/test_users_api.py

import httpx

DAO_SERVICE_URL = "http://flux-dao-service:8000"  # Docker internal network

async def example_goal_creation_flow():
    async with httpx.AsyncClient(base_url=DAO_SERVICE_URL) as client:
        # 1. Create a user
        user_resp = await client.post("/api/v1/users/", json={
            "email": "jane@example.com",
            "onboarded": False,
        })
        user_id = user_resp.json()["id"]

        # 2. Create a goal
        goal_resp = await client.post("/api/v1/goals/", json={
            "user_id": user_id,
            "title": "Run a marathon",
            "class_tags": ["health"],
            "target_weeks": 12,
            "status": "active",
        })
        goal_id = goal_resp.json()["id"]
        print(f"Created goal: {goal_id}")

        # 3. Create tasks linked to the goal
        for title in ["Run 5km", "Stretch routine"]:
            await client.post("/api/v1/tasks/", json={
                "user_id": user_id,
                "goal_id": goal_id,
                "title": title,
                "trigger_type": "time",
            })

        # 4. Query tasks by time range (used by Scheduler)
        tasks_resp = await client.get("/api/v1/tasks/by-timerange", params={
            "user_id": user_id,
            "start_at": "2026-03-01T00:00:00+00:00",
            "end_at": "2026-03-07T23:59:59+00:00",
        })
        tasks = tasks_resp.json()
```

**Key files to reference for calling patterns:**
- `backend/dao_service/tests/integration/test_api/test_tasks_api.py` — Scheduler endpoints (time range, bulk update, calendar sync)
- `backend/dao_service/tests/integration/test_api/test_goals_api.py` — Goal creation with structure
- `backend/dao_service/api/deps.py` — Authentication setup (`X-Flux-Service-Key`)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` on port 54322 | Supabase not running. Run `supabase start` |
| `asyncpg` build fails | Install binary wheel: `pip install --only-binary=:all: asyncpg` |
| Docker build fails | Ensure Docker Desktop is running and you're in the project root |
| Tests fail with `TRUNCATE` error | Supabase migration not applied. Run `bash scripts/supabase_setup.sh` |
| `409 Conflict` on create | Duplicate unique field (e.g., `langgraph_thread_id`). Use a different value. |

---

## Critical Files

1. `backend/dao_service/core/database.py`
   **Purpose**: DatabaseSession protocol + async engine foundation

2. `backend/dao_service/dao/dao_protocols.py`
   **Purpose**: Abstract DAO contracts (framework-agnostic with DatabaseSession)

3. `backend/dao_service/dao/dao_factory.py`
   **Purpose**: Abstract factory protocol (DaoFactoryProtocol)

4. `backend/dao_service/dao/dao_registry.py`
   **Purpose**: Framework selection logic

5. `backend/dao_service/dao/factories/dao_sqlalchemy_factory.py`
   **Purpose**: SQLAlchemy concrete factory (DaoSqlalchemyFactory)

6. `backend/dao_service/models/task_model.py`
   **Purpose**: Most complex ORM model (pattern for others)

7. `backend/dao_service/dao/impl/sqlalchemy/dao_task.py`
   **Purpose**: Reference DAO implementation (DaoTask class)

8. `backend/dao_service/repositories/dao_unit_of_work.py`
   **Purpose**: Framework-agnostic transaction coordinator (DaoUnitOfWork)

9. `backend/dao_service/services/dao_task_service.py`
   **Purpose**: Reference service pattern (data validation only, DaoTaskService class)

10. `backend/dao_service/api/deps.py`
    **Purpose**: FastAPI dependencies (get_db, verify_service_key, service factories)

---

## OpenAPI Compliance

**FastAPI Auto-Generates OpenAPI 3.0 Specification**:

```python
# dao_service/main.py
from fastapi import FastAPI

app = FastAPI(
    title="Flux Data Access API",
    description="Framework-agnostic data persistence microservice",
    version="1.0.0",
    openapi_tags=[
        {"name": "users", "description": "User operations"},
        {"name": "goals", "description": "Goal management"},
        {"name": "tasks", "description": "Task operations (includes Scheduler & Observer endpoints)"},
        {"name": "conversations", "description": "Conversation history"},
        {"name": "patterns", "description": "Behavioral pattern signals"},
        {"name": "notification-log", "description": "Notification delivery logs"},
    ]
)

# Automatic OpenAPI docs available at:
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/redoc (ReDoc)
# - http://localhost:8000/openapi.json (OpenAPI spec)
```

---

## Conclusion

This design provides a **scalable, framework-agnostic, enterprise-grade** Data Access microservice for Flux. Key achievements:

✅ **Framework Independence**: Switch ORMs with 1-line config change
✅ **Clean Architecture**: Strict layer separation (ORM ↔ DTO ↔ DAO ↔ Service ↔ API)
✅ **Data-Only Service**: NO business logic (belongs in Goal Planner/Scheduler/Observer)
✅ **Enterprise Naming**: Clear `dao_` prefix convention
✅ **ACID Transactions**: Full transactional support via Unit of Work
✅ **OpenAPI Compliant**: Auto-generated documentation with FastAPI
✅ **Test Coverage**: Comprehensive unit, integration, and E2E tests

**Implementation Complete**: 152 tests passing (103 unit + 49 integration) against Supabase PostgreSQL. Dockerized as an internal microservice on the `flux-internal` network.

---

**Document End**

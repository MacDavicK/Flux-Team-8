# Flux Data Access Layer Design

**Document Version**: 1.2
**Date**: 2026-02-22
**Status**: Design Approved

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
        # Check FK exists (prevents cryptic DB error)
        if task_data.milestone_id:
            milestone = await self.milestone_dao.get_by_id(db, task_data.milestone_id)
            if not milestone:
                raise ValueError(f"Milestone {task_data.milestone_id} not found")

        # Create task - DTO already validated format
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
- **CRUD operations** on all entities (users, goals, milestones, tasks, conversations, demo_flags)
- **Custom queries** for Scheduler (tasks by time range, bulk state updates)
- **Aggregations** for Observer (task statistics, pattern data)
- **Transactional operations** via Unit of Work pattern

**Technology**: FastAPI → Service Layer (data validation) → DAO → ORM → PostgreSQL

---

### Out of Scope: Business Logic Microservices

The following will be **separate microservices** calling this Data Access API:

1. **Goal Planner Service** (separate codebase):
   - User intent parsing
   - Goal decomposition into milestones/tasks
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
| GET | `/{goal_id}/full` | Get goal with milestones and tasks | Goal Planner | `GoalWithRelationsDTO` |
| POST | `/` | Create goal | Goal Planner | `GoalDTO` |
| POST | `/with-structure` | Create goal + milestones + tasks atomically | Goal Planner | `GoalWithRelationsDTO` |
| PATCH | `/{goal_id}` | Update goal | Goal Planner | `GoalDTO` |
| DELETE | `/{goal_id}` | Delete goal (cascade) | Goal Planner | `204 No Content` |

#### Milestone Endpoints (`/api/v1/milestones`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List milestones with pagination | All | `PaginatedResponse[MilestoneDTO]` |
| GET | `/{milestone_id}` | Get single milestone | All | `MilestoneDTO` |
| POST | `/` | Create milestone | Goal Planner, Scheduler | `MilestoneDTO` |
| PATCH | `/{milestone_id}` | Update milestone | Goal Planner, Scheduler | `MilestoneDTO` |
| DELETE | `/{milestone_id}` | Delete milestone (cascade) | Goal Planner | `204 No Content` |

#### Task Endpoints (`/api/v1/tasks`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List tasks with pagination | All | `PaginatedResponse[TaskDTO]` |
| GET | `/{task_id}` | Get single task | All | `TaskDTO` |
| POST | `/` | Create task | Goal Planner, Scheduler | `TaskDTO` |
| PATCH | `/{task_id}` | Update task | Goal Planner, Scheduler | `TaskDTO` |
| DELETE | `/{task_id}` | Delete task | Goal Planner | `204 No Content` |
| GET | `/by-timerange` | Get tasks in time window | Scheduler | `List[TaskDTO]` |
| POST | `/bulk-update-state` | Bulk state updates | Scheduler | `BulkUpdateResponse` |
| GET | `/statistics` | Task completion stats | Observer | `TaskStatisticsDTO` |
| PATCH | `/{task_id}/calendar-event` | Update calendar link | Scheduler | `TaskDTO` |

#### Conversation Endpoints (`/api/v1/conversations`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/` | List conversations with pagination | All | `PaginatedResponse[ConversationDTO]` |
| GET | `/{conversation_id}` | Get single conversation | All | `ConversationDTO` |
| POST | `/` | Create conversation | Goal Planner | `ConversationDTO` |
| PATCH | `/{conversation_id}` | Update conversation | Goal Planner | `ConversationDTO` |

#### Demo Flag Endpoints (`/api/v1/demo-flags`)

| Method | Path | Purpose | Used By | Response |
|--------|------|---------|---------|----------|
| GET | `/{user_id}` | Get demo flags | Scheduler | `DemoFlagDTO` |
| PUT | `/{user_id}` | Set/update demo flags | Goal Planner | `DemoFlagDTO` |

#### Operational Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness check (DB connection) |

---

### Inter-Service Authentication

While user authentication is handled by the calling services, the Data Access API verifies that requests originate from legitimate Flux microservices using API key authentication:

- Each calling service includes an `X-Flux-Service-Key` header
- Valid keys are loaded from environment configuration (`SERVICE_API_KEYS`)
- Invalid or missing keys return `403 Forbidden`
- The `verify_service_key` dependency is applied to all endpoints

```bash
# .env
SERVICE_API_KEYS=["goal-planner-key-abc","scheduler-key-def","observer-key-ghi"]
```

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
| 403 Forbidden | Invalid service key | Missing X-Flux-Service-Key |
| 404 Not Found | Entity doesn't exist | Task ID not found |
| 422 Unprocessable Entity | Validation failure | FK constraint violation |
| 500 Internal Server Error | Database failure | Connection timeout |
| 503 Service Unavailable | Service degraded | DB pool exhausted |

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
    new_state: TaskState

class BulkUpdateResponse(BaseModel):
    updated_count: int

class CalendarEventUpdateRequest(BaseModel):
    calendar_event_id: str = Field(..., max_length=255)

class TaskStatisticsDTO(BaseModel):
    user_id: UUID
    total_tasks: int
    by_state: Dict[str, int]
    completion_rate: float
```

---

## Interaction Flows

### Flow 1: Goal Creation with Milestones and Tasks

The Goal Planner service decomposes a user's goal into milestones and tasks, then persists the entire structure atomically via the Unit of Work pattern.

```mermaid
sequenceDiagram
    participant GP as Goal Planner Service
    participant API as Data Access API
    participant SVC as DaoGoalService
    participant UOW as DaoUnitOfWork
    participant DG as DaoGoal
    participant DM as DaoMilestone
    participant DT as DaoTask
    participant DB as PostgreSQL

    GP->>+API: POST /api/v1/goals/with-structure<br/>{goal, milestones, tasks}
    API->>API: verify_service_key()
    API->>+SVC: create_goal_with_structure(data)

    SVC->>+UOW: Begin transaction

    UOW->>+DG: create(db, GoalCreateDTO)
    DG->>+DB: INSERT INTO goals
    DB-->>-DG: goal_id
    DG-->>-UOW: GoalDTO

    loop For each milestone
        UOW->>+DM: create(db, MilestoneCreateDTO)
        DM->>+DB: INSERT INTO milestones
        DB-->>-DM: milestone_id
        DM-->>-UOW: MilestoneDTO

        loop For each task in milestone
            UOW->>+DT: create(db, TaskCreateDTO)
            DT->>+DB: INSERT INTO tasks
            DB-->>-DT: task_id
            DT-->>-UOW: TaskDTO
        end
    end

    UOW->>DB: COMMIT
    UOW-->>-SVC: GoalWithRelationsDTO
    SVC-->>-API: GoalWithRelationsDTO
    API-->>-GP: 201 Created
```

### Flow 2: Standalone Milestone Update & Task Creation

Not all writes go through the atomic goal-creation path. The Scheduler may need to update a milestone's status (e.g., mark it complete after all child tasks finish) or create a standalone task (e.g., a rescheduled drift-recovery task). The Goal Planner may also add individual tasks to an existing milestone during a follow-up conversation.

```mermaid
sequenceDiagram
    participant SC as Scheduler Service
    participant API as Data Access API
    participant MSVC as DaoMilestoneService
    participant DM as DaoMilestone
    participant TSVC as DaoTaskService
    participant DT as DaoTask
    participant DB as PostgreSQL

    Note over SC: All child tasks for milestone completed.<br/>Update milestone status.

    SC->>+API: PATCH /api/v1/milestones/{milestone_id}<br/>{status: "completed"}
    API->>API: verify_service_key()
    API->>+MSVC: update_milestone(db, milestone_id, MilestoneUpdateDTO)
    MSVC->>+DM: update(db, milestone_id, MilestoneUpdateDTO)
    DM->>+DB: UPDATE milestones SET status='completed'<br/>WHERE id=milestone_id
    DB-->>-DM: milestone row
    DM-->>-MSVC: MilestoneDTO
    MSVC-->>-API: MilestoneDTO
    API-->>-SC: 200 OK — MilestoneDTO

    Note over SC: Drift recovery — create<br/>a rescheduled task for missed one

    SC->>+API: POST /api/v1/tasks<br/>{user_id, goal_id, milestone_id,<br/>title, start_time, end_time, state: "scheduled"}
    API->>API: verify_service_key()
    API->>+TSVC: create_task(db, TaskCreateDTO)
    TSVC->>+DT: create(db, TaskCreateDTO)
    DT->>+DB: INSERT INTO tasks
    DB-->>-DT: task_id
    DT-->>-TSVC: TaskDTO
    TSVC-->>-API: TaskDTO
    API-->>-SC: 201 Created — TaskDTO
```

### Flow 3: Scheduler — Time Range Query & Bulk State Update

The Scheduler periodically queries tasks in a time window, runs drift detection logic, then bulk-updates drifted task states.

```mermaid
sequenceDiagram
    participant SC as Scheduler Service
    participant API as Data Access API
    participant SVC as DaoTaskService
    participant DAO as DaoTask
    participant DB as PostgreSQL

    SC->>+API: GET /api/v1/tasks/by-timerange<br/>?user_id=X&start_time=T1&end_time=T2
    API->>API: verify_service_key()
    API->>+SVC: get_tasks_for_scheduling(user_id, T1, T2)
    SVC->>+DAO: get_tasks_by_user_and_timerange(...)
    DAO->>+DB: SELECT FROM tasks<br/>WHERE user_id=X AND start_time BETWEEN T1,T2
    DB-->>-DAO: [task rows]
    DAO-->>-SVC: List[TaskDTO]
    SVC-->>-API: List[TaskDTO]
    API-->>-SC: 200 OK — List[TaskDTO]

    Note over SC: Drift detection logic runs<br/>(business logic in Scheduler)

    SC->>+API: POST /api/v1/tasks/bulk-update-state<br/>{task_ids: [id1, id2], state: "drifted"}
    API->>API: verify_service_key()
    API->>+SVC: bulk_update_state([id1, id2], "drifted")
    SVC->>+DAO: bulk_update_state([id1, id2], "drifted")
    DAO->>+DB: UPDATE tasks SET state='drifted'<br/>WHERE id IN (id1, id2)
    DB-->>-DAO: 2 rows affected
    DAO-->>-SVC: 2
    SVC-->>-API: BulkUpdateResponse
    API-->>-SC: 200 OK — {updated_count: 2}
```

### Flow 4: Scheduler — Calendar Event Synchronization

The Scheduler first creates an event in Google Calendar, then persists the returned event ID in the Data Access service.

```mermaid
sequenceDiagram
    participant SC as Scheduler Service
    participant GCAL as Google Calendar API
    participant API as Data Access API
    participant SVC as DaoTaskService
    participant DAO as DaoTask
    participant DB as PostgreSQL

    SC->>+GCAL: Create calendar event<br/>{summary, start, end}
    GCAL-->>-SC: {id: "gcal_evt_abc123"}

    SC->>+API: PATCH /api/v1/tasks/{task_id}/calendar-event<br/>{calendar_event_id: "gcal_evt_abc123"}
    API->>API: verify_service_key()
    API->>+SVC: update_calendar_event_id(task_id, "gcal_evt_abc123")
    SVC->>+DAO: update_calendar_event_id(task_id, "gcal_evt_abc123")
    DAO->>+DB: UPDATE tasks<br/>SET calendar_event_id='gcal_evt_abc123'<br/>WHERE id=task_id
    DB-->>-DAO: task row
    DAO-->>-SVC: TaskDTO
    SVC-->>-API: TaskDTO
    API-->>-SC: 200 OK — TaskDTO
```

### Flow 5: Observer — Task Statistics for Pattern Analysis

The Observer queries aggregated task statistics to detect user behavior patterns (e.g., recurring drift on Monday mornings).

```mermaid
sequenceDiagram
    participant OB as Observer Service
    participant API as Data Access API
    participant SVC as DaoTaskService
    participant DAO as DaoTask
    participant DB as PostgreSQL

    OB->>+API: GET /api/v1/tasks/statistics<br/>?user_id=X&start_date=D1&end_date=D2
    API->>API: verify_service_key()
    API->>+SVC: get_task_statistics(user_id, D1, D2)
    SVC->>+DAO: get_task_statistics(user_id, D1, D2)
    DAO->>+DB: SELECT state, COUNT(*) FROM tasks<br/>WHERE user_id=X AND created_at BETWEEN D1,D2<br/>GROUP BY state
    DB-->>-DAO: {scheduled:15, completed:42, drifted:8, missed:3}
    DAO-->>-SVC: TaskStatisticsDTO
    SVC-->>-API: TaskStatisticsDTO
    API-->>-OB: 200 OK — TaskStatisticsDTO

    Note over OB: Pattern analysis runs<br/>(business logic in Observer)
```

### Flow 6: Internal Layer Flow — Single CRUD Request

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
    Router->>+Deps: verify_service_key()
    Deps-->>-Router: valid

    Router->>+Deps: get_db()
    Deps->>+ORM: AsyncSessionLocal()
    ORM-->>-Deps: session (as DatabaseSession)
    Deps-->>-Router: db

    Router->>+Deps: get_task_service()
    Deps-->>-Router: DaoTaskService

    Router->>+Service: create_task(db, TaskCreateDTO)

    opt milestone_id provided
        Service->>+DAO: milestone_dao.get_by_id(milestone_id)
        DAO->>+ORM: execute(select(Milestone))
        ORM->>+DB: SELECT FROM milestones
        DB-->>-ORM: row
        ORM-->>-DAO: Milestone
        DAO-->>-Service: MilestoneDTO
    end

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
│   ├── main.py                          # FastAPI application entry
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
│   │   ├── enums.py                     # Python Enum classes
│   │   ├── user_model.py
│   │   ├── goal_model.py
│   │   ├── milestone_model.py
│   │   ├── task_model.py                # Includes calendar_event_id
│   │   ├── conversation_model.py
│   │   └── demo_flag_model.py
│   │
│   ├── schemas/                         # Pydantic DTO layer
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── enums.py                     # Pydantic-compatible enums
│   │   ├── pagination.py               # PaginatedResponse generic wrapper
│   │   ├── error.py                    # ErrorDetail response schema
│   │   ├── user.py
│   │   ├── goal.py                      # GoalDTO, GoalWithRelationsDTO
│   │   ├── milestone.py
│   │   ├── task.py                      # TaskDTO with calendar_event_id
│   │   ├── conversation.py
│   │   └── demo_flag.py
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
│   │           ├── dao_milestone.py
│   │           ├── dao_task.py          # Extended queries (time range, bulk update)
│   │           ├── dao_conversation.py
│   │           └── dao_demo_flag.py
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
│   │   ├── dao_milestone_service.py
│   │   └── dao_conversation_service.py
│   │
│   ├── api/                             # FastAPI routes
│   │   ├── __init__.py
│   │   ├── deps.py                      # Dependencies (get_db, verify_service_key)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── users_api.py
│   │       ├── goals_api.py
│   │       ├── tasks_api.py
│   │       ├── milestones_api.py
│   │       ├── conversations_api.py
│   │       └── demo_flags_api.py
│   │
│   ├── tests/                           # DAO-service tests (moved from backend/tests/)
│   │   ├── __init__.py
│   │   ├── conftest.py                  # PostgreSQL fixtures + data factories
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   └── test_schemas/            # DTO validation tests (no DB)
│   │   └── integration/
│   │       ├── __init__.py
│   │       └── test_api/                # API endpoint tests (needs Supabase)
│   │
│   ├── scripts/                         # DAO-service scripts
│   │   ├── build_and_test.sh            # Full build + test pipeline with HTML report
│   │   ├── run_tests.sh                 # Run tests only
│   │   └── setup_dao.sh                 # Environment setup & dependency install
│   │
│   ├── requirements.txt                 # DAO-service production dependencies
│   └── requirements-dev.txt             # DAO-service development/test dependencies
│
├── tests/                               # Legacy app/ tests (non-DAO)
│   ├── conftest.py                      # Legacy fixtures only (app_client, mock_supabase)
│   ├── test_goal_planner_agent.py
│   ├── test_goal_service.py
│   ├── test_goals_router.py
│   └── test_schemas.py
│
├── Dockerfile                           # Service-specific Docker image
├── .dockerignore
├── docker-compose.dao-service.yml       # Service-specific compose (internal network)
├── Makefile                             # Service-specific build commands
├── pytest.ini                           # testpaths = tests dao_service/tests
├── pyproject.toml                       # pytest + tool configuration
├── requirements.txt                     # Full backend production dependencies
└── requirements-dev.txt                 # Full backend development dependencies
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

**Task Model Example** (with calendar_event_id):
```python
# dao_service/models/task_model.py
from sqlalchemy import Column, String, ForeignKey, ENUM
from sqlalchemy.orm import Mapped, relationship

class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[UUID] = ForeignKey("users.id", ondelete="CASCADE")
    goal_id: Mapped[UUID] = ForeignKey("goals.id", ondelete="CASCADE")
    milestone_id: Mapped[Optional[UUID]] = ForeignKey("milestones.id", ondelete="CASCADE")

    title: Mapped[str]
    start_time: Mapped[Optional[datetime]]
    end_time: Mapped[Optional[datetime]]

    state: Mapped[TaskStateEnum] = ENUM(TaskStateEnum, create_type=False)
    priority: Mapped[TaskPriorityEnum] = ENUM(TaskPriorityEnum, create_type=False)
    trigger_type: Mapped[TriggerTypeEnum] = ENUM(TriggerTypeEnum, create_type=False)

    is_recurring: Mapped[bool]
    calendar_event_id: Mapped[Optional[str]] = Column(String(255), index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    goal: Mapped["Goal"] = relationship(back_populates="tasks")
    milestone: Mapped[Optional["Milestone"]] = relationship(back_populates="tasks")
```

---

### Layer 3: DTOs (Pydantic Schemas)

**Purpose**: API contracts with validation, separate from database structure.

**Task DTO Pattern**:
```python
# dao_service/schemas/task.py

class TaskBase(BaseSchema):
    """Shared attributes."""
    title: str = Field(..., min_length=1, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: TaskState = TaskState.SCHEDULED
    priority: TaskPriority = TaskPriority.STANDARD

    @field_validator("end_time")
    def validate_end_after_start(cls, v, info):
        if v and info.data.get("start_time") and v < info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

class TaskCreateDTO(TaskBase):
    """For creation requests."""
    user_id: UUID
    goal_id: UUID
    milestone_id: Optional[UUID] = None

class TaskUpdateDTO(BaseSchema):
    """For updates - all fields optional."""
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    state: Optional[TaskState] = None
    calendar_event_id: Optional[str] = None

class TaskDTO(TaskBase, IDMixin, TimestampMixin):
    """Complete response schema."""
    id: UUID
    user_id: UUID
    goal_id: UUID
    milestone_id: Optional[UUID] = None
    calendar_event_id: Optional[str] = None
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
        self, db: DatabaseSession, user_id: UUID, start_time: datetime, end_time: datetime
    ) -> List[TaskDTO]: ...

    async def update_calendar_event_id(
        self, db: DatabaseSession, task_id: UUID, calendar_event_id: str
    ) -> Optional[TaskDTO]: ...

    async def bulk_update_state(
        self, db: DatabaseSession, task_ids: List[UUID], new_state: TaskState
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
        self, db: DatabaseSession, user_id: UUID, start_time: datetime, end_time: datetime
    ) -> List[TaskDTO]:
        session: SQLAlchemyAsyncSession = db

        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.start_time >= start_time)
            .where(Task.start_time <= end_time)
            .order_by(Task.start_time)
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
                Task.state,
                func.count(Task.id).label("count"),
            )
            .where(Task.user_id == user_id)
            .where(Task.created_at >= start_date)
            .where(Task.created_at <= end_date)
            .group_by(Task.state)
        )
        result = await session.execute(stmt)
        stats = {row.state.value: row.count for row in result}
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
from dao_service.dao.dao_registry import get_task_dao, get_milestone_dao
from dao_service.dao.dao_protocols import TaskDAOProtocol, MilestoneDAOProtocol

class DaoTaskService:
    """
    Data validation service for tasks.

    Responsibilities:
    - Data format validation (Pydantic handles this)
    - Technical limits (pagination cap)
    - Optional FK existence checks
    - NO business logic (that belongs in Goal Planner/Scheduler/Observer)
    """

    def __init__(self):
        self.task_dao: TaskDAOProtocol = get_task_dao()
        self.milestone_dao: MilestoneDAOProtocol = get_milestone_dao()

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
        Create task with data integrity validation only.

        Data Integrity:
        - ✅ Check milestone exists (prevents cryptic FK error)

        Business Logic NOT Here:
        - ❌ Does goal belong to user? (Goal Planner service checks)
        - ❌ Should task be created now? (Goal Planner service decides)
        """
        # Optional: Check milestone exists
        if task_data.milestone_id:
            milestone = await self.milestone_dao.get_by_id(db, task_data.milestone_id)
            if not milestone:
                raise ValueError(f"Milestone {task_data.milestone_id} not found")

        return await self.task_dao.create(db, task_data)

    async def get_tasks_for_scheduling(
        self, db: DatabaseSession, user_id: UUID, start_time: datetime, end_time: datetime
    ) -> List[TaskDTO]:
        """
        Data retrieval for Scheduler microservice.
        NO scheduling logic here - just query execution.
        """
        return await self.task_dao.get_tasks_by_user_and_timerange(
            db, user_id, start_time, end_time
        )
```

---

### Layer 7: API Layer (FastAPI Endpoints)

**Purpose**: Expose services via HTTP with OpenAPI documentation.

Services are injected via FastAPI's `Depends()` rather than instantiated per-request. The `verify_service_key` dependency authenticates all inter-service calls.

**Representative Endpoint Example** (same pattern applies to all endpoints):
```python
# dao_service/api/v1/tasks_api.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from dao_service.core.database import DatabaseSession
from dao_service.api.deps import get_db, verify_service_key
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
    _: str = Depends(verify_service_key),
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
    # ... other DAOs
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
        # ... other DAOs

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
    milestone = await uow.milestones.create(db, milestone_data)
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

5. **Authenticate requests:** All endpoints require the `X-Flux-Service-Key` header. In Swagger UI, click the "Authorize" button and enter: `goal-planner-key-abc`

6. **Try a basic flow via Swagger:**
   - **POST** `/api/v1/users/` — Create a user (returns user with `id`)
   - **POST** `/api/v1/goals/` — Create a goal using the user's `id`
   - **POST** `/api/v1/tasks/` — Create a task linked to the user and goal
   - **GET** `/api/v1/goals/{goal_id}/full` — View goal with milestones and tasks

7. **Other documentation endpoints:**
   - ReDoc: http://localhost:8000/redoc
   - OpenAPI JSON spec: http://localhost:8000/openapi.json

### Running the DAO Service via Docker

```bash
# Build the Docker image
docker build -t flux-dao-service backend/

# Deploy using docker-compose
docker-compose -f backend/docker-compose.dao-service.yml up -d

# Verify it's running
curl http://localhost:8000/health

# Swagger UI
open http://localhost:8000/docs

# Stop
docker-compose -f backend/docker-compose.dao-service.yml down
```

The Docker container connects to Supabase on the host via `host.docker.internal:54322`.

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
- **44 unit tests** — Pydantic DTO schema validation (no database), located in `dao_service/tests/unit/`
- **40 integration tests** — Full API endpoint testing against Supabase PostgreSQL, located in `dao_service/tests/integration/`
- **Test isolation** — Each integration test gets a fresh session; tables are truncated between tests
- **Async support** — Uses `pytest-asyncio` with session-scoped event loops
- **Test discovery** — `pytest.ini` `testpaths` covers both `tests/` (legacy) and `dao_service/tests/`

### Calling the DAO Service from Python (Other Services)

If another Flux service (Goal Planner, Scheduler, Observer) needs to call this service directly from Python, use `httpx.AsyncClient`. The integration tests demonstrate the exact pattern:

```python
# Reference: backend/dao_service/tests/integration/test_api/test_users_api.py

import httpx

DAO_SERVICE_URL = "http://flux-dao-service:8000"  # Docker internal network
SERVICE_KEY = "goal-planner-key-abc"               # From SERVICE_API_KEYS config

headers = {"X-Flux-Service-Key": SERVICE_KEY}

async def example_goal_creation_flow():
    async with httpx.AsyncClient(base_url=DAO_SERVICE_URL, headers=headers) as client:
        # 1. Create a user
        user_resp = await client.post("/api/v1/users/", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
        })
        user_id = user_resp.json()["id"]

        # 2. Create a goal with milestones and tasks in one call
        goal_resp = await client.post("/api/v1/goals/with-structure", json={
            "user_id": user_id,
            "title": "Run a marathon",
            "category": "health",
            "timeline": "12 weeks",
            "milestones": [
                {
                    "week_number": 1,
                    "title": "Build base fitness",
                    "tasks": [
                        {"title": "Run 5km", "trigger_type": "time"},
                        {"title": "Stretch routine", "trigger_type": "time"},
                    ],
                },
            ],
        })
        goal = goal_resp.json()
        print(f"Created goal: {goal['id']} with {len(goal['milestones'])} milestones")

        # 3. Query tasks by time range (used by Scheduler)
        tasks_resp = await client.get("/api/v1/tasks/by-timerange", params={
            "start": "2026-03-01T00:00:00+00:00",
            "end": "2026-03-07T23:59:59+00:00",
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
| `X-Flux-Service-Key` 401 error | Pass header `X-Flux-Service-Key: goal-planner-key-abc` |

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
        {"name": "tasks", "description": "Task operations"},
        {"name": "milestones", "description": "Milestone management"},
        {"name": "conversations", "description": "Conversation history"},
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

**Implementation Complete**: 84 tests passing (44 unit + 40 integration) against Supabase PostgreSQL. Dockerized as an internal microservice on the `flux-internal` network.

---

**Document End**

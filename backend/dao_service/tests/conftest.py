"""
Shared fixtures for dao_service tests.

Uses local Supabase PostgreSQL (port 54322) for integration tests.
Database tables are created by Supabase migration (20260213145903_create_mvp_tables.sql).

Clean-state pattern:
- Each test gets a fresh database session
- Tables are truncated before each test to ensure isolation
- No cross-test state leakage
"""

from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from dao_service.models.base import Base
from dao_service.models import Conversation, DemoFlag, Goal, Milestone, Task, User  # noqa: F401
from dao_service.core.database import get_db
from dao_service.api.deps import verify_service_key
from dao_service.main import app

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create the async engine inside the session event loop.

    asyncpg binds connections to the loop they were created on,
    so the engine MUST be created within the pytest-asyncio session loop.
    NullPool avoids connection caching across event loop contexts.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(test_engine):
    """
    Truncate all tables once per test session to ensure clean starting state.

    NOT autouse — only triggered by integration tests that depend on db_session/client.
    Unit tests (schema validation) do not need a database connection.
    """
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE users CASCADE;"))
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE users CASCADE;"))


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.

    Creates a fresh engine per test to avoid asyncpg event-loop binding issues.
    Uses truncation between tests for isolation.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    session = AsyncSession(bind=engine, expire_on_commit=False)
    yield session
    await session.close()
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users CASCADE;"))
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with DB and auth overrides."""

    async def override_get_db():
        yield db_session

    async def override_verify_service_key():
        return "test-key"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_service_key] = override_verify_service_key

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# --- Synthetic Data Factories ---


def make_user_data(**overrides) -> dict:
    """Generate user creation data with sensible defaults."""
    defaults = {
        "name": f"Test User {uuid4().hex[:6]}",
        "email": f"test-{uuid4().hex[:8]}@flux.test",
        "preferences": {},
        "demo_mode": False,
    }
    defaults.update(overrides)
    return defaults


def make_goal_data(user_id: str, **overrides) -> dict:
    """Generate goal creation data."""
    defaults = {
        "user_id": user_id,
        "title": f"Test Goal {uuid4().hex[:6]}",
        "category": "health",
        "timeline": "4 weeks",
        "status": "active",
    }
    defaults.update(overrides)
    return defaults


def make_milestone_data(goal_id: str, **overrides) -> dict:
    """Generate milestone creation data."""
    defaults = {
        "goal_id": goal_id,
        "week_number": 1,
        "title": f"Test Milestone {uuid4().hex[:6]}",
        "status": "pending",
    }
    defaults.update(overrides)
    return defaults


def make_task_data(user_id: str, goal_id: str, **overrides) -> dict:
    """Generate task creation data."""
    defaults = {
        "user_id": user_id,
        "goal_id": goal_id,
        "title": f"Test Task {uuid4().hex[:6]}",
        "state": "scheduled",
        "priority": "standard",
        "trigger_type": "time",
        "is_recurring": False,
    }
    defaults.update(overrides)
    return defaults

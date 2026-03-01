"""
Shared fixtures for dao_service tests.

Uses local Supabase PostgreSQL (port 54322) for integration tests.
Database tables are created by Supabase migrations.

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
from dao_service.models import Conversation, Goal, Message, NotificationLog, Pattern, Task, User  # noqa: F401
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
        "email": f"test-{uuid4().hex[:8]}@flux.test",
        "onboarded": False,
        "profile": {},
        "notification_preferences": {
            "phone_number": None,
            "whatsapp_opted_in": False,
            "reminder_lead_minutes": 10,
            "escalation_window_minutes": 2,
        },
    }
    defaults.update(overrides)
    return defaults


def make_goal_data(user_id: str, **overrides) -> dict:
    """Generate goal creation data."""
    defaults = {
        "user_id": user_id,
        "title": f"Test Goal {uuid4().hex[:6]}",
        "description": "Test goal description",
        "class_tags": ["Health"],
        "status": "active",
        "target_weeks": 6,
    }
    defaults.update(overrides)
    return defaults


def make_conversation_data(user_id: str, **overrides) -> dict:
    """Generate conversation creation data."""
    defaults = {
        "user_id": user_id,
        "langgraph_thread_id": f"thread-{uuid4().hex[:12]}",
        "context_type": "goal",
    }
    defaults.update(overrides)
    return defaults


def make_message_data(conversation_id: str, **overrides) -> dict:
    """Generate message creation data."""
    defaults = {
        "conversation_id": conversation_id,
        "role": "user",
        "content": f"Test message {uuid4().hex[:6]}",
        "input_modality": "text",
    }
    defaults.update(overrides)
    return defaults


def make_task_data(user_id: str, goal_id: str | None = None, **overrides) -> dict:
    """Generate task creation data."""
    defaults = {
        "user_id": user_id,
        "goal_id": goal_id,
        "title": f"Test Task {uuid4().hex[:6]}",
        "status": "pending",
        "trigger_type": "time",
        "duration_minutes": 30,
    }
    defaults.update(overrides)
    return defaults

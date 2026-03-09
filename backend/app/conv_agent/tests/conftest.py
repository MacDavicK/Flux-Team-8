"""
Fixtures for conv_agent integration tests.

Uses real local Supabase (localhost:54322) and dao_service via ASGITransport.
"""

from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from dao_service.core.database import get_db
from dao_service.api.deps import verify_service_key
from dao_service.main import app as dao_app


@pytest_asyncio.fixture(scope="function")
async def dao_service_client():
    """dao_service app via in-process ASGI -- no real server needed."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

    async def override_get_db():
        session = AsyncSession(bind=engine, expire_on_commit=False)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def override_verify_service_key():
        return "test-key"

    dao_app.dependency_overrides[get_db] = override_get_db
    dao_app.dependency_overrides[verify_service_key] = override_verify_service_key

    transport = ASGITransport(app=dao_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    dao_app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_user(dao_service_client):
    """Create a real user in Supabase for testing. Yields user dict. Deletes on teardown."""
    resp = await dao_service_client.post(
        "/api/v1/users/",
        json={"email": f"test_{uuid4().hex[:8]}@conv-agent-test.com"},
    )
    assert resp.status_code == 201, f"Failed to create user: {resp.text}"
    user = resp.json()
    yield user
    await dao_service_client.delete(f"/api/v1/users/{user['id']}")


@pytest_asyncio.fixture(scope="function")
async def conv_agent_client(dao_service_client):
    """
    Main app client with dao_client injected to use the test dao_service.

    Overrides get_dao_client in both voice_service and intent_handler
    to return a client that talks to the in-process dao_service.
    """
    from unittest.mock import patch
    from app.conv_agent.dao_client import ConvAgentDaoClient

    # Create a dao client that uses the test dao_service via ASGITransport
    test_dao_client = ConvAgentDaoClient(
        base_url="http://test",
        service_key="test-key",
        client=dao_service_client,
    )

    try:
        from app.main import app as main_app
    except ImportError:
        # If main app can't import (missing deps), skip
        import pytest
        pytest.skip("Main app dependencies not available")

    with (
        patch("app.conv_agent.voice_service.get_dao_client", return_value=test_dao_client),
        patch("app.conv_agent.intent_handler.get_dao_client", return_value=test_dao_client),
    ):
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

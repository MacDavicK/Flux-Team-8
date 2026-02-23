"""Integration tests for operational endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestOperationalEndpoints:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_ready(self, client: AsyncClient):
        # In test environment with SQLite, readiness check may not fully work
        # but the endpoint itself should not error
        resp = await client.get("/ready")
        assert resp.status_code == 200

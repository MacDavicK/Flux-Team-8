"""Integration tests for Pattern API endpoints."""

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_user_data


@pytest.mark.asyncio
class TestPatternEndpoints:
    async def _create_user(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/users/", json=make_user_data())
        return resp.json()["id"]

    async def test_create_pattern(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = {
            "user_id": user_id,
            "pattern_type": "completion_streak",
            "description": "Good adherence this week",
            "data": {"streak_days": 4},
            "confidence": 0.8,
        }
        resp = await client.post("/api/v1/patterns/", json=data)
        assert resp.status_code == 201
        assert resp.json()["pattern_type"] == "completion_streak"

    async def test_get_pattern_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/patterns/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_get_update_delete_pattern(self, client: AsyncClient):
        user_id = await self._create_user(client)
        create_resp = await client.post(
            "/api/v1/patterns/",
            json={
                "user_id": user_id,
                "pattern_type": "time_avoidance",
                "confidence": 0.5,
            },
        )
        pattern_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/v1/patterns/{pattern_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == pattern_id

        patch_resp = await client.patch(
            f"/api/v1/patterns/{pattern_id}",
            json={"confidence": 0.9, "description": "Improved confidence"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["confidence"] == 0.9

        del_resp = await client.delete(f"/api/v1/patterns/{pattern_id}")
        assert del_resp.status_code == 204

        get_deleted_resp = await client.get(f"/api/v1/patterns/{pattern_id}")
        assert get_deleted_resp.status_code == 404

    async def test_list_patterns_pagination(self, client: AsyncClient):
        user_id = await self._create_user(client)
        for i in range(3):
            await client.post(
                "/api/v1/patterns/",
                json={
                    "user_id": user_id,
                    "pattern_type": f"pattern_{i}",
                    "confidence": 0.4,
                },
            )

        resp = await client.get("/api/v1/patterns/?skip=0&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["page_size"] == 2
        assert len(body["items"]) <= 2

    async def test_update_pattern_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/patterns/00000000-0000-0000-0000-000000000000",
            json={"confidence": 0.6},
        )
        assert resp.status_code == 404

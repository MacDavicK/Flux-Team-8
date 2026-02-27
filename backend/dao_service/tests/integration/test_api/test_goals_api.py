"""Integration tests for Goal API endpoints."""

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_goal_data, make_user_data


@pytest.mark.asyncio
class TestGoalCRUD:
    async def _create_user(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/users/", json=make_user_data())
        return resp.json()["id"]

    async def test_create_goal(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = make_goal_data(user_id)
        resp = await client.post("/api/v1/goals/", json=data)
        assert resp.status_code == 201
        assert resp.json()["title"] == data["title"]
        assert resp.json()["class_tags"] == ["Health"]

    async def test_get_goal_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/goals/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_update_goal(self, client: AsyncClient):
        user_id = await self._create_user(client)
        create_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = create_resp.json()["id"]

        resp = await client.patch(f"/api/v1/goals/{goal_id}", json={"status": "completed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    async def test_delete_goal(self, client: AsyncClient):
        user_id = await self._create_user(client)
        create_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/goals/{goal_id}")
        assert del_resp.status_code == 204

    async def test_list_goals_pagination(self, client: AsyncClient):
        user_id = await self._create_user(client)
        for _ in range(3):
            await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        resp = await client.get("/api/v1/goals/?skip=0&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page_size"] == 2
        assert len(body["items"]) <= 2

    async def test_create_goal_invalid_status(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = make_goal_data(user_id, status="draft")
        resp = await client.post("/api/v1/goals/", json=data)
        assert resp.status_code == 422

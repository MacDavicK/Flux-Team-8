"""Integration tests for Milestone API endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import make_goal_data, make_milestone_data, make_user_data


@pytest.mark.asyncio
class TestMilestoneEndpoints:
    async def _create_user_and_goal(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]
        return user_id, goal_id

    async def test_create_milestone(self, client: AsyncClient):
        _, goal_id = await self._create_user_and_goal(client)
        data = make_milestone_data(goal_id)
        resp = await client.post("/api/v1/milestones/", json=data)
        assert resp.status_code == 201
        assert resp.json()["goal_id"] == goal_id

    async def test_create_milestone_invalid_goal_id(self, client: AsyncClient):
        """FK check: goal_id that doesn't exist should return 422."""
        data = make_milestone_data("00000000-0000-0000-0000-000000000000")
        resp = await client.post("/api/v1/milestones/", json=data)
        assert resp.status_code == 422

    async def test_get_milestone(self, client: AsyncClient):
        _, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/milestones/", json=make_milestone_data(goal_id))
        ms_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/milestones/{ms_id}")
        assert resp.status_code == 200

    async def test_update_milestone_status(self, client: AsyncClient):
        """Scheduler updates milestone status to 'completed'."""
        _, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/milestones/", json=make_milestone_data(goal_id))
        ms_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/milestones/{ms_id}", json={"status": "completed"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    async def test_delete_milestone(self, client: AsyncClient):
        _, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/milestones/", json=make_milestone_data(goal_id))
        ms_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/milestones/{ms_id}")
        assert del_resp.status_code == 204

    async def test_list_milestones_paginated(self, client: AsyncClient):
        resp = await client.get("/api/v1/milestones/")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

"""Integration tests for Goal API endpoints including atomic structure creation."""

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


@pytest.mark.asyncio
class TestGoalWithStructure:
    """Tests for POST /goals/with-structure — atomic goal + milestones + tasks creation."""

    async def _create_user(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/users/", json=make_user_data())
        return resp.json()["id"]

    async def test_create_goal_with_milestones_and_tasks(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = {
            "goal": {
                "user_id": user_id,
                "title": "Run a 10K",
                "category": "fitness",
                "timeline": "8 weeks",
            },
            "milestones": [
                {
                    "week_number": 1,
                    "title": "Build base endurance",
                    "tasks": [
                        {"title": "Run 2km"},
                        {"title": "Stretch 15 min"},
                    ],
                },
                {
                    "week_number": 2,
                    "title": "Increase distance",
                    "tasks": [
                        {"title": "Run 5km"},
                    ],
                },
            ],
        }

        resp = await client.post("/api/v1/goals/with-structure", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Run a 10K"
        assert len(body["milestones"]) == 2
        assert len(body["tasks"]) == 3
        assert body["milestones"][0]["title"] == "Build base endurance"

    async def test_create_goal_with_empty_milestones(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = {
            "goal": {"user_id": user_id, "title": "Minimal goal"},
            "milestones": [],
        }
        resp = await client.post("/api/v1/goals/with-structure", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["milestones"] == []
        assert body["tasks"] == []

    async def test_get_goal_full(self, client: AsyncClient):
        user_id = await self._create_user(client)
        # Create via structure endpoint
        data = {
            "goal": {"user_id": user_id, "title": "Full goal"},
            "milestones": [
                {
                    "week_number": 1,
                    "title": "MS1",
                    "tasks": [{"title": "Task A"}],
                }
            ],
        }
        create_resp = await client.post("/api/v1/goals/with-structure", json=data)
        goal_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/goals/{goal_id}/full")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["milestones"]) == 1
        assert len(body["tasks"]) == 1

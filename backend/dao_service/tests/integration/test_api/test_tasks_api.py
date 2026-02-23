"""Integration tests for Task API endpoints — CRUD, scheduler, and observer flows."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_goal_data, make_task_data, make_user_data


@pytest.mark.asyncio
class TestTaskCRUD:
    """Standard task CRUD operations."""

    async def _create_user_and_goal(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]
        return user_id, goal_id

    async def test_create_task(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        data = make_task_data(user_id, goal_id)
        resp = await client.post("/api/v1/tasks/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == data["title"]
        assert body["status"] == "pending"
        assert body["user_id"] == user_id
        assert body["goal_id"] == goal_id

    async def test_get_task(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))
        task_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    async def test_get_task_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_list_tasks_paginated(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        for _ in range(3):
            await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))

        resp = await client.get("/api/v1/tasks/?skip=0&limit=2")
        body = resp.json()
        assert len(body["items"]) <= 2
        assert "total" in body

    async def test_update_task(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))
        task_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "done"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    async def test_delete_task(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))
        task_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/tasks/{task_id}")
        assert del_resp.status_code == 204

    async def test_create_task_without_goal_id(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        data = make_task_data(user_id, None)
        resp = await client.post("/api/v1/tasks/", json=data)
        assert resp.status_code == 201
        assert resp.json()["goal_id"] is None

    async def test_create_task_invalid_status(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        data = make_task_data(user_id, goal_id, status="queued")
        resp = await client.post("/api/v1/tasks/", json=data)
        assert resp.status_code == 422

@pytest.mark.asyncio
class TestTaskSchedulerEndpoints:
    """Scheduler-specific endpoints: time range and bulk status update."""

    async def _setup_tasks(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]

        now = datetime.now(timezone.utc)
        task_ids = []
        for i in range(3):
            data = make_task_data(
                user_id,
                goal_id,
                scheduled_at=(now + timedelta(hours=i)).isoformat(),
                duration_minutes=30,
            )
            resp = await client.post("/api/v1/tasks/", json=data)
            task_ids.append(resp.json()["id"])

        return user_id, goal_id, task_ids, now

    async def test_get_tasks_by_timerange(self, client: AsyncClient):
        user_id, goal_id, task_ids, now = await self._setup_tasks(client)
        start = (now - timedelta(hours=1)).isoformat()
        end = (now + timedelta(hours=5)).isoformat()

        resp = await client.get(
            "/api/v1/tasks/by-timerange",
            params={"user_id": user_id, "start_at": start, "end_at": end},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    async def test_get_tasks_by_timerange_empty(self, client: AsyncClient):
        """No tasks in the requested window."""
        user_id, goal_id, task_ids, now = await self._setup_tasks(client)
        future = (now + timedelta(days=30)).isoformat()
        far_future = (now + timedelta(days=31)).isoformat()

        resp = await client.get(
            "/api/v1/tasks/by-timerange",
            params={"user_id": user_id, "start_at": future, "end_at": far_future},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_bulk_update_status(self, client: AsyncClient):
        user_id, goal_id, task_ids, now = await self._setup_tasks(client)

        resp = await client.post(
            "/api/v1/tasks/bulk-update-state",
            json={"task_ids": task_ids[:2], "new_status": "rescheduled"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 2

        # Verify the tasks actually changed
        for tid in task_ids[:2]:
            get_resp = await client.get(f"/api/v1/tasks/{tid}")
            assert get_resp.json()["status"] == "rescheduled"

    async def test_bulk_update_nonexistent_tasks(self, client: AsyncClient):
        """Bulk update with IDs that don't exist returns 0."""
        resp = await client.post(
            "/api/v1/tasks/bulk-update-state",
            json={
                "task_ids": ["00000000-0000-0000-0000-000000000000"],
                "new_status": "done",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 0


@pytest.mark.asyncio
class TestTaskObserverEndpoints:
    """Observer-specific endpoints: statistics."""

    async def test_get_task_statistics(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]

        # Create tasks in different statuses
        for status in ["pending", "done", "done", "rescheduled"]:
            data = make_task_data(user_id, goal_id, status=status)
            await client.post("/api/v1/tasks/", json=data)

        now = datetime.now(timezone.utc)
        start = (now - timedelta(hours=1)).isoformat()
        end = (now + timedelta(hours=1)).isoformat()

        resp = await client.get(
            "/api/v1/tasks/statistics",
            params={"user_id": user_id, "start_date": start, "end_date": end},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == user_id
        assert body["total_tasks"] == 4
        assert body["by_status"]["done"] == 2
        assert body["completion_rate"] == 0.5

    async def test_statistics_no_tasks(self, client: AsyncClient):
        """Edge case: user with no tasks in range."""
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]

        now = datetime.now(timezone.utc)
        start = (now - timedelta(hours=1)).isoformat()
        end = (now + timedelta(hours=1)).isoformat()

        resp = await client.get(
            "/api/v1/tasks/statistics",
            params={"user_id": user_id, "start_date": start, "end_date": end},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_tasks"] == 0
        assert body["completion_rate"] == 0.0
        assert body["by_status"] == {}

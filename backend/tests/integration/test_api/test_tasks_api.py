"""Integration tests for Task API endpoints — CRUD, scheduler, and observer flows."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import make_goal_data, make_task_data, make_user_data


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
        assert body["state"] == "scheduled"
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
            json={"state": "completed"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "completed"

    async def test_delete_task(self, client: AsyncClient):
        user_id, goal_id = await self._create_user_and_goal(client)
        create_resp = await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))
        task_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/tasks/{task_id}")
        assert del_resp.status_code == 204

    async def test_create_task_invalid_milestone_id(self, client: AsyncClient):
        """FK check: milestone_id that doesn't exist should return 422."""
        user_id, goal_id = await self._create_user_and_goal(client)
        data = make_task_data(
            user_id, goal_id, milestone_id="00000000-0000-0000-0000-000000000000"
        )
        resp = await client.post("/api/v1/tasks/", json=data)
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestTaskSchedulerEndpoints:
    """Scheduler-specific endpoints: time range, bulk update, calendar event."""

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
                start_time=(now + timedelta(hours=i)).isoformat(),
                end_time=(now + timedelta(hours=i + 1)).isoformat(),
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
            params={"user_id": user_id, "start_time": start, "end_time": end},
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
            params={"user_id": user_id, "start_time": future, "end_time": far_future},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_bulk_update_state(self, client: AsyncClient):
        user_id, goal_id, task_ids, now = await self._setup_tasks(client)

        resp = await client.post(
            "/api/v1/tasks/bulk-update-state",
            json={"task_ids": task_ids[:2], "new_state": "drifted"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 2

        # Verify the tasks actually changed
        for tid in task_ids[:2]:
            get_resp = await client.get(f"/api/v1/tasks/{tid}")
            assert get_resp.json()["state"] == "drifted"

    async def test_bulk_update_nonexistent_tasks(self, client: AsyncClient):
        """Bulk update with IDs that don't exist returns 0."""
        resp = await client.post(
            "/api/v1/tasks/bulk-update-state",
            json={
                "task_ids": ["00000000-0000-0000-0000-000000000000"],
                "new_state": "completed",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 0

    async def test_update_calendar_event_id(self, client: AsyncClient):
        user_id, goal_id, task_ids, now = await self._setup_tasks(client)
        task_id = task_ids[0]

        resp = await client.patch(
            f"/api/v1/tasks/{task_id}/calendar-event",
            json={"calendar_event_id": "gcal_evt_abc123"},
        )
        assert resp.status_code == 200
        assert resp.json()["calendar_event_id"] == "gcal_evt_abc123"

    async def test_update_calendar_event_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/calendar-event",
            json={"calendar_event_id": "gcal_xyz"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestTaskObserverEndpoints:
    """Observer-specific endpoints: statistics."""

    async def test_get_task_statistics(self, client: AsyncClient):
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]

        # Create tasks in different states
        for state in ["scheduled", "completed", "completed", "drifted"]:
            data = make_task_data(user_id, goal_id, state=state)
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
        assert body["by_state"]["completed"] == 2
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
        assert body["by_state"] == {}

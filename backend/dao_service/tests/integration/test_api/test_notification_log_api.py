"""Integration tests for Notification Log API endpoints."""

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_goal_data, make_task_data, make_user_data


@pytest.mark.asyncio
class TestNotificationLogEndpoints:
    async def _create_task(self, client: AsyncClient) -> str:
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        goal_resp = await client.post("/api/v1/goals/", json=make_goal_data(user_id))
        goal_id = goal_resp.json()["id"]
        task_resp = await client.post("/api/v1/tasks/", json=make_task_data(user_id, goal_id))
        return task_resp.json()["id"]

    async def test_create_notification_log(self, client: AsyncClient):
        task_id = await self._create_task(client)
        data = {"task_id": task_id, "channel": "push"}
        resp = await client.post("/api/v1/notification-log/", json=data)
        assert resp.status_code == 201
        assert resp.json()["task_id"] == task_id
        assert resp.json()["channel"] == "push"

    async def test_create_notification_log_invalid_channel(self, client: AsyncClient):
        task_id = await self._create_task(client)
        data = {"task_id": task_id, "channel": "sms"}
        resp = await client.post("/api/v1/notification-log/", json=data)
        assert resp.status_code == 422

    async def test_get_update_delete_notification_log(self, client: AsyncClient):
        task_id = await self._create_task(client)
        create_resp = await client.post(
            "/api/v1/notification-log/",
            json={"task_id": task_id, "channel": "push", "response": "done"},
        )
        assert create_resp.status_code == 201
        log_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/v1/notification-log/{log_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == log_id

        patch_resp = await client.patch(
            f"/api/v1/notification-log/{log_id}",
            json={"channel": "whatsapp", "response": "reschedule"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["channel"] == "whatsapp"
        assert patch_resp.json()["response"] == "reschedule"

        del_resp = await client.delete(f"/api/v1/notification-log/{log_id}")
        assert del_resp.status_code == 204

        get_deleted_resp = await client.get(f"/api/v1/notification-log/{log_id}")
        assert get_deleted_resp.status_code == 404

    async def test_list_notification_logs_pagination(self, client: AsyncClient):
        task_id = await self._create_task(client)
        for _ in range(3):
            await client.post(
                "/api/v1/notification-log/",
                json={"task_id": task_id, "channel": "push"},
            )

        resp = await client.get("/api/v1/notification-log/?skip=0&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["page_size"] == 2
        assert len(body["items"]) <= 2

    async def test_update_notification_log_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/notification-log/00000000-0000-0000-0000-000000000000",
            json={"channel": "push"},
        )
        assert resp.status_code == 404

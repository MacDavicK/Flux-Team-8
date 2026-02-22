"""Integration tests for Conversation API endpoints."""

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_user_data


@pytest.mark.asyncio
class TestConversationEndpoints:
    async def _create_user(self, client: AsyncClient) -> str:
        resp = await client.post("/api/v1/users/", json=make_user_data())
        return resp.json()["id"]

    async def test_create_conversation(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = {
            "user_id": user_id,
            "langgraph_thread_id": "thread-create-1",
            "context_type": "goal",
        }
        resp = await client.post("/api/v1/conversations/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == user_id
        assert body["context_type"] == "goal"

    async def test_get_conversation_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_list_conversations_pagination(self, client: AsyncClient):
        user_id = await self._create_user(client)
        for i in range(3):
            await client.post(
                "/api/v1/conversations/",
                json={
                    "user_id": user_id,
                    "langgraph_thread_id": f"thread-list-{i}",
                    "context_type": "task",
                },
            )

        resp = await client.get("/api/v1/conversations/?skip=0&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["page_size"] == 2
        assert len(body["items"]) <= 2

    async def test_update_conversation(self, client: AsyncClient):
        user_id = await self._create_user(client)
        create_resp = await client.post(
            "/api/v1/conversations/",
            json={
                "user_id": user_id,
                "langgraph_thread_id": "thread-update-1",
                "context_type": "onboarding",
            },
        )
        conversation_id = create_resp.json()["id"]

        patch_resp = await client.patch(
            f"/api/v1/conversations/{conversation_id}",
            json={"context_type": "reschedule"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["context_type"] == "reschedule"

    async def test_update_conversation_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/conversations/00000000-0000-0000-0000-000000000000",
            json={"context_type": "task"},
        )
        assert resp.status_code == 404

    async def test_create_conversation_invalid_context_type(self, client: AsyncClient):
        user_id = await self._create_user(client)
        resp = await client.post(
            "/api/v1/conversations/",
            json={
                "user_id": user_id,
                "langgraph_thread_id": "thread-invalid-context",
                "context_type": "chat",
            },
        )
        assert resp.status_code == 422

    async def test_create_conversation_duplicate_thread_id_rejected(self, client: AsyncClient):
        user_id = await self._create_user(client)
        data = {
            "user_id": user_id,
            "langgraph_thread_id": "thread-unique-1",
            "context_type": "goal",
        }
        first_resp = await client.post("/api/v1/conversations/", json=data)
        assert first_resp.status_code == 201

        # langgraph_thread_id has a UNIQUE constraint in the DB.
        # The global IntegrityError handler normalises this to 409 Conflict.
        second_resp = await client.post("/api/v1/conversations/", json=data)
        assert second_resp.status_code == 409

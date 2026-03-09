"""Integration tests for Message API endpoints -- CRUD operations."""

import pytest
from httpx import AsyncClient

from dao_service.tests.conftest import make_conversation_data, make_message_data, make_user_data


@pytest.mark.asyncio
class TestMessageCRUD:
    """Message endpoint integration tests."""

    async def _create_user_and_conversation(self, client: AsyncClient):
        """Helper: create a user and a conversation, return their IDs."""
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        conv_resp = await client.post(
            "/api/v1/conversations/",
            json=make_conversation_data(user_id),
        )
        conv_id = conv_resp.json()["id"]
        return user_id, conv_id

    async def test_create_message(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        data = make_message_data(conv_id)
        resp = await client.post("/api/v1/messages/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "user"
        assert body["conversation_id"] == conv_id

    async def test_list_messages_by_conversation(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        for i in range(3):
            await client.post(
                "/api/v1/messages/",
                json=make_message_data(conv_id, content=f"Message {i}"),
            )
        resp = await client.get(
            "/api/v1/messages/", params={"conversation_id": conv_id}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_get_message_by_id(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        create_resp = await client.post(
            "/api/v1/messages/", json=make_message_data(conv_id)
        )
        msg_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/messages/{msg_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == msg_id

    async def test_get_message_not_found(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/messages/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    async def test_delete_message(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        create_resp = await client.post(
            "/api/v1/messages/", json=make_message_data(conv_id)
        )
        msg_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/messages/{msg_id}")
        assert del_resp.status_code == 204

    async def test_delete_message_not_found(self, client: AsyncClient):
        resp = await client.delete(
            "/api/v1/messages/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    async def test_create_message_voice_modality(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        data = make_message_data(conv_id, input_modality="voice")
        resp = await client.post("/api/v1/messages/", json=data)
        assert resp.status_code == 201
        assert resp.json()["input_modality"] == "voice"

    async def test_create_message_all_roles(self, client: AsyncClient):
        _, conv_id = await self._create_user_and_conversation(client)
        for role in ("user", "assistant", "system", "function"):
            data = make_message_data(conv_id, role=role)
            resp = await client.post("/api/v1/messages/", json=data)
            assert resp.status_code == 201
            assert resp.json()["role"] == role

    async def test_messages_cascade_delete_with_conversation(self, client: AsyncClient):
        """Messages should be deleted when their parent user is deleted (cascade)."""
        user_resp = await client.post("/api/v1/users/", json=make_user_data())
        user_id = user_resp.json()["id"]
        conv_resp = await client.post(
            "/api/v1/conversations/",
            json=make_conversation_data(user_id),
        )
        conv_id = conv_resp.json()["id"]
        await client.post("/api/v1/messages/", json=make_message_data(conv_id))

        # Deleting the user cascades to conversations and messages
        del_resp = await client.delete(f"/api/v1/users/{user_id}")
        assert del_resp.status_code == 204

        # Messages should be gone
        msgs_resp = await client.get(
            "/api/v1/messages/", params={"conversation_id": conv_id}
        )
        assert msgs_resp.status_code == 200
        assert len(msgs_resp.json()) == 0

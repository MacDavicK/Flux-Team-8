"""Integration tests for User API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import make_user_data


@pytest.mark.asyncio
class TestUserEndpoints:
    async def test_create_user(self, client: AsyncClient):
        data = make_user_data()
        resp = await client.post("/api/v1/users/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == data["name"]
        assert body["email"] == data["email"]
        assert "id" in body
        assert "created_at" in body

    async def test_get_user(self, client: AsyncClient):
        data = make_user_data()
        create_resp = await client.post("/api/v1/users/", json=data)
        user_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id

    async def test_get_user_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_list_users_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body

    async def test_list_users_pagination(self, client: AsyncClient):
        # Create 3 users
        for _ in range(3):
            await client.post("/api/v1/users/", json=make_user_data())

        resp = await client.get("/api/v1/users/?skip=0&limit=2")
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page_size"] == 2

    async def test_update_user(self, client: AsyncClient):
        data = make_user_data()
        create_resp = await client.post("/api/v1/users/", json=data)
        user_id = create_resp.json()["id"]

        update_resp = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"name": "Updated Name"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Name"

    async def test_update_user_not_found(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_delete_user(self, client: AsyncClient):
        data = make_user_data()
        create_resp = await client.post("/api/v1/users/", json=data)
        user_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/users/{user_id}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/users/{user_id}")
        assert get_resp.status_code == 404

    async def test_delete_user_not_found(self, client: AsyncClient):
        resp = await client.delete("/api/v1/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_create_user_invalid_empty_name(self, client: AsyncClient):
        resp = await client.post("/api/v1/users/", json={"name": "", "email": "x@y.z"})
        assert resp.status_code == 422

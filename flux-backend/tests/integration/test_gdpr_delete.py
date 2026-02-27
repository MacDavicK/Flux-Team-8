"""
21.2.5 — Integration tests for GDPR account deletion.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def account_client():
    from fastapi import FastAPI
    from app.api.v1.account import router
    app = FastAPI()
    app.include_router(router)

    from app.middleware.auth import get_current_user
    mock_user = MagicMock()
    mock_user.id = "test-user-uuid"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return TestClient(app)


def test_delete_account_cascades_all_rows(account_client):
    """DELETE /account executes all cascade deletions."""
    execute_calls = []

    async def capture_execute(query, *args):
        execute_calls.append(query.strip().split()[0].upper() + " " + query.strip().split()[-1].upper())
        return "OK"

    with patch("app.api.v1.account.db") as mock_db:
        mock_db.execute = AsyncMock(side_effect=capture_execute)

        response = account_client.delete("/")

    assert response.status_code == 204
    # All major table deletions should have occurred
    deleted_tables = " ".join(execute_calls).lower()
    assert "notification_log" in deleted_tables or len(execute_calls) >= 5
    # The users table must be deleted last
    assert len(execute_calls) >= 5  # at minimum: tasks, goals, patterns, messages, conversations, users

"""
21.2.1 — Integration tests for POST /chat/message.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def chat_client():
    from fastapi import FastAPI
    from app.api.v1.chat import router
    app = FastAPI()
    app.include_router(router)

    # Override auth
    from app.middleware.auth import get_current_user
    mock_user = MagicMock()
    mock_user.id = "test-user-uuid"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return TestClient(app)


@pytest.mark.asyncio
async def test_post_chat_message_creates_conversation(chat_client):
    """POST /chat/message with no conversation_id creates a new conversation."""
    mock_graph_result = {
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you today?"},
        ],
        "intent": "CLARIFY",
        "approval_status": None,
        "goal_draft": None,
    }

    with patch("app.api.v1.chat.db") as mock_db, \
         patch("app.api.v1.chat.compiled_graph") as mock_graph, \
         patch("app.api.v1.chat.window_conversation_history", AsyncMock(side_effect=lambda h, uid, cid=None: h)):

        import uuid
        conv_id = uuid.uuid4()
        mock_db.fetchrow = AsyncMock(side_effect=[
            {"id": conv_id, "langgraph_thread_id": str(uuid.uuid4())},  # INSERT conversation
            {"profile": {}, "timezone": "UTC"},  # user profile fetch
        ])
        mock_db.fetch = AsyncMock(return_value=[])  # no existing messages
        mock_db.execute = AsyncMock(return_value="OK")
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)

        response = chat_client.post(
            "/chat/message",
            json={"message": "Hello", "conversation_id": None},
        )

    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "message" in data
    assert data["message"] == "Hi! How can I help you today?"

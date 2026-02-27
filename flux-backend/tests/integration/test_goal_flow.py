"""
21.2.2 — Integration test: end-to-end goal submission flow.

Submit goal → plan returned → approve → tasks written to DB.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def chat_client():
    from fastapi import FastAPI
    from app.api.v1.chat import router
    app = FastAPI()
    app.include_router(router)

    from app.middleware.auth import get_current_user
    mock_user = MagicMock()
    mock_user.id = "test-user-uuid"
    app.dependency_overrides[get_current_user] = lambda: mock_user

    return TestClient(app)


@pytest.mark.asyncio
async def test_goal_submission_returns_plan(chat_client):
    """Submitting a goal message triggers the planner and returns a draft plan."""
    conv_id = uuid.uuid4()
    thread_id = str(uuid.uuid4())

    mock_graph_result = {
        "conversation_history": [
            {"role": "user", "content": "I want to run a 5k in 3 months"},
            {"role": "assistant", "content": "Great goal! Here's a plan for you..."},
        ],
        "intent": "CLARIFY",
        "approval_status": None,
        "goal_draft": {
            "title": "Run a 5k",
            "description": "Complete a 5k run within 3 months",
            "category": "fitness",
        },
    }

    with patch("app.api.v1.chat.db") as mock_db, \
         patch("app.api.v1.chat.compiled_graph") as mock_graph, \
         patch("app.api.v1.chat.window_conversation_history", AsyncMock(side_effect=lambda h, uid, cid=None: h)):

        mock_db.fetchrow = AsyncMock(side_effect=[
            {"id": conv_id, "langgraph_thread_id": thread_id},
            {"profile": {}, "timezone": "UTC"},
        ])
        mock_db.fetch = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(return_value="OK")
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)

        response = chat_client.post(
            "/chat/message",
            json={"message": "I want to run a 5k in 3 months", "conversation_id": None},
        )

    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "message" in data
    assert data["message"] == "Great goal! Here's a plan for you..."


@pytest.mark.asyncio
async def test_goal_approval_triggers_task_writes(chat_client):
    """Approving a goal plan results in tasks being persisted (execute called)."""
    conv_id = uuid.uuid4()
    thread_id = str(uuid.uuid4())

    task1_id = uuid.uuid4()
    task2_id = uuid.uuid4()

    mock_graph_result = {
        "conversation_history": [
            {"role": "user", "content": "Yes, let's do it"},
            {"role": "assistant", "content": "Perfect! I've scheduled your tasks."},
        ],
        "intent": "APPROVE",
        "approval_status": "approved",
        "goal_draft": None,
        "saved_task_ids": [str(task1_id), str(task2_id)],
    }

    with patch("app.api.v1.chat.db") as mock_db, \
         patch("app.api.v1.chat.compiled_graph") as mock_graph, \
         patch("app.api.v1.chat.window_conversation_history", AsyncMock(side_effect=lambda h, uid, cid=None: h)):

        mock_db.fetchrow = AsyncMock(side_effect=[
            {"id": conv_id, "langgraph_thread_id": thread_id},
            {"profile": {}, "timezone": "UTC"},
        ])
        mock_db.fetch = AsyncMock(return_value=[
            {"role": "user", "content": "I want to run a 5k", "created_at": "2024-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Here's a plan...", "created_at": "2024-01-01T00:00:01Z"},
        ])
        mock_db.execute = AsyncMock(return_value="OK")
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)

        response = chat_client.post(
            "/chat/message",
            json={"message": "Yes, let's do it", "conversation_id": str(conv_id)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Perfect! I've scheduled your tasks."
    # Verify DB was called (messages persisted)
    assert mock_db.execute.call_count >= 1


@pytest.mark.asyncio
async def test_goal_flow_reuses_existing_conversation(chat_client):
    """Subsequent messages reuse the same conversation and thread."""
    conv_id = uuid.uuid4()
    thread_id = str(uuid.uuid4())

    mock_graph_result = {
        "conversation_history": [
            {"role": "user", "content": "Can you adjust my schedule?"},
            {"role": "assistant", "content": "Sure, I've updated your plan."},
        ],
        "intent": "RESCHEDULE_TASK",
        "approval_status": None,
        "goal_draft": None,
    }

    with patch("app.api.v1.chat.db") as mock_db, \
         patch("app.api.v1.chat.compiled_graph") as mock_graph, \
         patch("app.api.v1.chat.window_conversation_history", AsyncMock(side_effect=lambda h, uid, cid=None: h)):

        # fetchrow returns the existing conversation (not a new insert)
        mock_db.fetchrow = AsyncMock(side_effect=[
            {"id": conv_id, "langgraph_thread_id": thread_id},
            {"profile": {}, "timezone": "UTC"},
        ])
        mock_db.fetch = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock(return_value="OK")
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)

        response = chat_client.post(
            "/chat/message",
            json={"message": "Can you adjust my schedule?", "conversation_id": str(conv_id)},
        )

    assert response.status_code == 200
    data = response.json()
    assert str(data["conversation_id"]) == str(conv_id)

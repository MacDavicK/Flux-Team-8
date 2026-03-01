"""
Conv Agent Integration Tests.

Uses real local Supabase + real Deepgram API (no mocking).
Mocks ONLY the intent handlers (_handle_goal, _handle_create_task,
_handle_reschedule_task).

Requirements:
  - Local Supabase running (localhost:54322)
  - DEEPGRAM_API_KEY env var set
  - dao_service dependencies installed
  - Main app dependencies installed (openai, langchain, etc.)

Run:
  cd backend && DEEPGRAM_API_KEY=<key> pytest conv_agent/tests/test_integration.py -v -m integration
"""

import os

import pytest

pytestmark = pytest.mark.integration

skip_no_key = pytest.mark.skipif(
    not os.getenv("DEEPGRAM_API_KEY"),
    reason="DEEPGRAM_API_KEY env var not set",
)


@skip_no_key
@pytest.mark.asyncio
async def test_create_session_returns_real_deepgram_token(conv_agent_client, test_user):
    """POST /api/v1/voice/session mints a real Deepgram JWT (not mock string)."""
    resp = await conv_agent_client.post(
        "/api/v1/voice/session", json={"user_id": test_user["id"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["deepgram_token"] != "MOCK_DEEPGRAM_TOKEN_FOR_TESTING"
    assert len(data["deepgram_token"]) > 20  # real JWT
    assert data["config"]["system_prompt"]
    assert len(data["config"]["functions"]) == 3


@skip_no_key
@pytest.mark.asyncio
async def test_save_message_and_retrieve_from_supabase(conv_agent_client, test_user):
    """Messages are persisted to real Supabase and retrievable."""
    # Create session
    session_resp = await conv_agent_client.post(
        "/api/v1/voice/session", json={"user_id": test_user["id"]}
    )
    session_id = session_resp.json()["session_id"]

    # Save a message
    save_resp = await conv_agent_client.post(
        "/api/v1/voice/messages",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "I want to learn Spanish",
        },
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "saved"

    # Retrieve messages
    get_resp = await conv_agent_client.get(
        f"/api/v1/voice/sessions/{session_id}/messages"
    )
    assert get_resp.status_code == 200
    messages = get_resp.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "I want to learn Spanish"


@skip_no_key
@pytest.mark.asyncio
async def test_process_intent_calls_mocked_goal_handler(conv_agent_client, test_user):
    """POST /api/v1/voice/intents with submit_goal_intent uses mock handler."""
    from unittest.mock import patch, AsyncMock

    session_resp = await conv_agent_client.post(
        "/api/v1/voice/session", json={"user_id": test_user["id"]}
    )
    session_id = session_resp.json()["session_id"]

    mock_handler = AsyncMock(return_value="Goal noted (test mock)")
    with patch("conv_agent.intent_handler._handle_goal", mock_handler):
        intent_resp = await conv_agent_client.post(
            "/api/v1/voice/intents",
            json={
                "session_id": session_id,
                "function_call_id": "fc_test_001",
                "function_name": "submit_goal_intent",
                "input": {"goal_statement": "Learn Spanish", "timeline": "3 months"},
            },
        )
    assert intent_resp.status_code == 200
    assert "Goal noted" in intent_resp.json()["result"]


@skip_no_key
@pytest.mark.asyncio
async def test_close_session_updates_supabase(conv_agent_client, test_user):
    """DELETE /api/v1/voice/session/{id} marks session closed in real Supabase."""
    session_resp = await conv_agent_client.post(
        "/api/v1/voice/session", json={"user_id": test_user["id"]}
    )
    session_id = session_resp.json()["session_id"]

    # Save a couple of messages
    for content in ["Hello", "I want to run a marathon"]:
        await conv_agent_client.post(
            "/api/v1/voice/messages",
            json={"session_id": session_id, "role": "user", "content": content},
        )

    close_resp = await conv_agent_client.delete(
        f"/api/v1/voice/session/{session_id}"
    )
    assert close_resp.status_code == 200
    data = close_resp.json()
    assert data["status"] == "closed"
    assert data["message_count"] == 2

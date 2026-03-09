"""
Flux Conv Agent -- Router Tests

FastAPI TestClient tests using patch_conv_agent() for full endpoint coverage.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from fastapi import FastAPI

from app.conv_agent.mocks import patch_conv_agent
from app.conv_agent.router import router as voice_router

# Minimal app for router tests — avoids importing app.main which
# pulls in langchain_text_splitters and other unrelated dependencies.
app = FastAPI()
app.include_router(voice_router)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_create_session_endpoint():
    """POST /api/v1/voice/session should return 200 with session_id, deepgram_token, config."""
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "deepgram_token" in data
        assert "config" in data


@pytest.mark.asyncio
async def test_save_message_endpoint():
    """POST /api/v1/voice/messages should return 200 with message_id."""
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First create a session
            session_resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
            session_id = session_resp.json()["session_id"]

            resp = await client.post(
                "/api/v1/voice/messages",
                json={
                    "session_id": session_id,
                    "role": "user",
                    "content": "Hello there",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data


@pytest.mark.asyncio
async def test_get_messages_endpoint():
    """GET /api/v1/voice/sessions/{id}/messages should return 200 with messages list."""
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create a session
            session_resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
            session_id = session_resp.json()["session_id"]

            resp = await client.get(f"/api/v1/voice/sessions/{session_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)


@pytest.mark.asyncio
async def test_process_intent_endpoint():
    """POST /api/v1/voice/intents with a goal intent should return 200 with result."""
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create a session
            session_resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
            session_id = session_resp.json()["session_id"]

            resp = await client.post(
                "/api/v1/voice/intents",
                json={
                    "session_id": session_id,
                    "function_call_id": "fc_test_001",
                    "function_name": "submit_goal_intent",
                    "input": {
                        "goal_statement": "Run a marathon",
                        "timeline": "6 months",
                    },
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data


@pytest.mark.asyncio
async def test_process_intent_response_includes_function_call_id():
    """
    POST /api/v1/voice/intents response must include function_call_id.

    Regression for: FunctionCallResponse field rename (output → content, added name).
    The backend echoes function_call_id so the frontend can match the response
    back to the right Deepgram call. If this field is missing the agent goes silent.
    """
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            session_resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
            session_id = session_resp.json()["session_id"]

            resp = await client.post(
                "/api/v1/voice/intents",
                json={
                    "session_id": session_id,
                    "function_call_id": "fc_regression_001",
                    "function_name": "submit_goal_intent",
                    "input": {"goal_statement": "Lose 5kg"},
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["function_call_id"] == "fc_regression_001", (
            "function_call_id must be echoed back so the frontend can send a "
            "correct FunctionCallResponse to Deepgram"
        )
        assert "result" in data
        assert isinstance(data["result"], str)


@pytest.mark.asyncio
async def test_process_intent_missing_function_name_returns_422():
    """
    POST /api/v1/voice/intents without function_name must return 422.

    Regression for: Deepgram V1 FunctionCallRequest format mismatch.
    Before the fix, the frontend was reading event.function_name (undefined in V1)
    and sending null to this endpoint, causing a silent 422 and no agent response.
    """
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/voice/intents",
                json={
                    "session_id": "some-session-id",
                    "function_call_id": "fc_test_002",
                    # function_name deliberately omitted
                    "input": {},
                },
            )
        assert resp.status_code == 422, (
            "Missing function_name must be caught by Pydantic before reaching "
            "the handler — a 422 here is the correct guard against the V1 format bug"
        )


@pytest.mark.asyncio
async def test_process_intent_missing_function_call_id_returns_422():
    """
    POST /api/v1/voice/intents without function_call_id must return 422.

    Regression for: Deepgram V1 FunctionCallRequest format mismatch.
    Before the fix, the frontend sent null for function_call_id (read from
    event.id which doesn't exist at the top level in V1 format).
    """
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/voice/intents",
                json={
                    "session_id": "some-session-id",
                    # function_call_id deliberately omitted
                    "function_name": "submit_goal_intent",
                    "input": {},
                },
            )
        assert resp.status_code == 422, (
            "Missing function_call_id must be caught by Pydantic — "
            "a 422 here surfaces the V1 format bug immediately in tests"
        )


@pytest.mark.asyncio
async def test_close_session_endpoint():
    """DELETE /api/v1/voice/session/{id} should return 200 with status 'closed'."""
    with patch_conv_agent():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create a session
            session_resp = await client.post(
                "/api/v1/voice/session",
                json={"user_id": "mock-user-id"},
            )
            session_id = session_resp.json()["session_id"]

            resp = await client.delete(f"/api/v1/voice/session/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "closed"

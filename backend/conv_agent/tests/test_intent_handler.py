"""
Flux Conv Agent -- Intent Handler Tests

Tests for intent_handler using in-memory mocks (no Supabase, no dao_service).
"""

from __future__ import annotations

import pytest

from conv_agent.mocks import patch_conv_agent
from conv_agent.intent_handler import handle_intent
from conv_agent import voice_service


async def _create_session() -> str:
    """Helper: create a mock session and return its ID."""
    return await voice_service.create_session("mock-user-id")


@pytest.mark.asyncio
async def test_handle_goal_intent_returns_confirmation():
    """submit_goal_intent should return a string containing 'Goal created'."""
    with patch_conv_agent():
        session_id = await _create_session()
        result = await handle_intent(
            "submit_goal_intent",
            {"goal_statement": "Learn Spanish", "timeline": "3 months"},
            session_id,
        )
        assert isinstance(result, str)
        assert "Goal created" in result


@pytest.mark.asyncio
async def test_handle_new_task_intent():
    """submit_new_task_intent should return a string containing 'Task created'."""
    with patch_conv_agent():
        session_id = await _create_session()
        result = await handle_intent(
            "submit_new_task_intent",
            {"title": "Call mom", "trigger_type": "time", "scheduled_at": "7pm"},
            session_id,
        )
        assert isinstance(result, str)
        assert "Task created" in result


@pytest.mark.asyncio
async def test_handle_reschedule_intent():
    """submit_reschedule_intent should return a string containing 'Rescheduled'."""
    with patch_conv_agent():
        session_id = await _create_session()
        result = await handle_intent(
            "submit_reschedule_intent",
            {"task_id": "task-abc-123", "preferred_new_time": "Friday 6pm"},
            session_id,
        )
        assert isinstance(result, str)
        assert "Rescheduled" in result


@pytest.mark.asyncio
async def test_handle_unknown_intent_returns_error_string():
    """An unknown function name should return an error string, not raise."""
    with patch_conv_agent():
        result = await handle_intent("unknown_function", {}, "")
        assert isinstance(result, str)
        assert "don't know" in result.lower() or "sorry" in result.lower()

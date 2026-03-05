"""
21.1.1 — Unit tests for orchestrator_node.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _make_state(conversation_history=None):
    return {
        "user_id": "test-user-id",
        "conversation_history": conversation_history or [{"role": "user", "content": "I want to run a 5K"}],
        "intent": None,
        "user_profile": {"timezone": "UTC"},
        "goal_draft": None,
        "proposed_tasks": None,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": "test-correlation-id",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("expected_intent", ["GOAL", "NEW_TASK", "CLARIFY", "RESCHEDULE_TASK", "MODIFY_GOAL"])
async def test_intent_classification(expected_intent):
    """Orchestrator correctly returns each intent type from validated_llm_call."""
    from app.models.agent_outputs import OrchestratorOutput

    mock_output = OrchestratorOutput(
        intent=expected_intent,
        payload={},
        clarification_question=None,
        task_id=None,
        goal_id=None,
    )

    with patch("app.agents.orchestrator.db") as mock_db, \
         patch("app.agents.orchestrator.check_token_budget", AsyncMock(return_value="ok")), \
         patch("app.agents.orchestrator.validated_llm_call", AsyncMock(return_value=mock_output)):

        mock_db.fetchrow = AsyncMock(return_value={"onboarded": True})

        from app.agents.orchestrator import orchestrator_node
        result = await orchestrator_node(_make_state())

    assert result["intent"] == expected_intent


@pytest.mark.asyncio
async def test_overrides_intent_to_onboarding_when_not_onboarded():
    """If user is not onboarded, intent is forced to ONBOARDING."""
    with patch("app.agents.orchestrator.db") as mock_db:
        mock_db.fetchrow = AsyncMock(return_value={"onboarded": False})

        from app.agents.orchestrator import orchestrator_node
        result = await orchestrator_node(_make_state())

    assert result["intent"] == "ONBOARDING"

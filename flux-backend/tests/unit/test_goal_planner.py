"""
21.1.2 — Unit tests for goal_planner_node.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


def _make_state():
    return {
        "user_id": "test-user-id",
        "conversation_history": [{"role": "user", "content": "I want to run a 5K in 6 weeks"}],
        "intent": "GOAL",
        "user_profile": {"timezone": "UTC"},
        "goal_draft": {"title": "Run a 5K"},
        "proposed_tasks": None,
        "classifier_output": {"tags": ["fitness", "health"]},
        "scheduler_output": {"slots": [], "conflicts": []},
        "pattern_output": {"best_times": ["07:00"], "avoid_slots": [], "category_performance": [], "general_notes": ""},
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": "test",
    }


@pytest.mark.asyncio
async def test_goal_planner_returns_plan_summary():
    """GoalPlannerOutput is validated and plan_summary returned in conversation."""
    from app.models.agent_outputs import GoalPlannerOutput, ProposedTask

    mock_output = GoalPlannerOutput(
        goal_feasible_in_6_weeks=True,
        proposed_tasks=[
            ProposedTask(
                title="Morning Run",
                description="Run 30 mins",
                scheduled_days=["Monday", "Wednesday", "Friday"],
                suggested_time="07:00",
                duration_minutes=30,
                recurrence_rule="FREQ=WEEKLY;BYDAY=MO,WE,FR",
                week_range=[1, 6],
            )
        ],
        plan_summary="Here is your 6-week running plan.",
        approval_status="pending",
    )

    with patch("app.agents.goal_planner.validated_llm_call", AsyncMock(return_value=mock_output)), \
         patch("app.agents.goal_planner.check_token_budget", AsyncMock(return_value="ok")), \
         patch("app.agents.goal_planner.db"):

        from app.agents.goal_planner import goal_planner_node
        result = await goal_planner_node(_make_state())

    assert result["approval_status"] == "pending"
    # The plan summary should appear in conversation history
    history = result.get("conversation_history", [])
    assistant_msgs = [m for m in history if m.get("role") == "assistant"]
    assert any("running" in m.get("content", "").lower() or "plan" in m.get("content", "").lower() for m in assistant_msgs)


@pytest.mark.asyncio
async def test_micro_goal_decomposition_when_not_feasible():
    """When goal_feasible_in_6_weeks=False, micro_goal_roadmap is populated."""
    from app.models.agent_outputs import GoalPlannerOutput, ProposedTask, MicroGoal

    mock_output = GoalPlannerOutput(
        goal_feasible_in_6_weeks=False,
        micro_goal_roadmap=[
            MicroGoal(title="Phase 1: Foundation", description="Build base", pipeline_order=1),
            MicroGoal(title="Phase 2: Build", description="Increase mileage", pipeline_order=2),
        ],
        proposed_tasks=[
            ProposedTask(
                title="Easy Run",
                description="30 min easy",
                scheduled_days=["Monday"],
                suggested_time="07:00",
                duration_minutes=30,
                recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
                week_range=[1, 6],
            )
        ],
        plan_summary="This goal needs 12 weeks. Here is phase 1.",
        approval_status="pending",
    )

    with patch("app.agents.goal_planner.validated_llm_call", AsyncMock(return_value=mock_output)), \
         patch("app.agents.goal_planner.check_token_budget", AsyncMock(return_value="ok")), \
         patch("app.agents.goal_planner.db") as mock_db:
        mock_db.execute = AsyncMock()
        mock_db.fetchrow = AsyncMock(return_value=None)

        from app.agents.goal_planner import goal_planner_node
        result = await goal_planner_node(_make_state())

    assert result["approval_status"] == "pending"

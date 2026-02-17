"""
Tests for Pydantic schemas — validation and serialization.
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    ConversationState,
    GoalConversationResponse,
    PlanMilestone,
    RespondRequest,
    StartGoalRequest,
    TaskPriority,
    TaskState,
)


class TestStartGoalRequest:
    def test_valid_request(self):
        req = StartGoalRequest(user_id="u1", message="I want to lose weight")
        assert req.user_id == "u1"
        assert req.message == "I want to lose weight"

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError):
            StartGoalRequest(message="hello")

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            StartGoalRequest(user_id="u1")


class TestRespondRequest:
    def test_valid(self):
        req = RespondRequest(message="March 15th")
        assert req.message == "March 15th"

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError):
            RespondRequest()


class TestPlanMilestone:
    def test_valid_milestone(self):
        m = PlanMilestone(week=1, title="Week 1", tasks=["walk", "gym"])
        assert m.week == 1
        assert len(m.tasks) == 2

    def test_empty_tasks_allowed(self):
        m = PlanMilestone(week=1, title="Week 1", tasks=[])
        assert m.tasks == []


class TestGoalConversationResponse:
    def test_minimal_response(self):
        r = GoalConversationResponse(
            conversation_id="c1",
            state=ConversationState.IDLE,
            message="Hello!",
        )
        assert r.plan is None
        assert r.goal_id is None

    def test_full_response_with_plan(self):
        r = GoalConversationResponse(
            conversation_id="c1",
            state=ConversationState.AWAITING_CONFIRMATION,
            message="Here's your plan",
            plan=[PlanMilestone(week=1, title="W1", tasks=["task1"])],
            goal_id="g1",
        )
        assert len(r.plan) == 1
        assert r.goal_id == "g1"


class TestEnums:
    def test_conversation_states(self):
        assert ConversationState.IDLE.value == "IDLE"
        assert ConversationState.CONFIRMED.value == "CONFIRMED"

    def test_task_state(self):
        assert TaskState.SCHEDULED.value == "scheduled"
        assert TaskState.DRIFTED.value == "drifted"

    def test_task_priority(self):
        assert TaskPriority.MUST_NOT_MISS.value == "must-not-miss"

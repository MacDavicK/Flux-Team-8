"""
Tests for the GoalPlannerAgent state machine.

Verifies state transitions, context extraction, serialization,
and fallback behavior — uses real OpenRouter calls via .env key.
"""

import pytest

from app.agents.goal_planner import GoalPlannerAgent
from app.models.schemas import ConversationState, PlanMilestone


@pytest.fixture()
def agent():
    """Fresh agent instance using real OpenRouter from .env."""
    return GoalPlannerAgent(conversation_id="test-conv-1", user_id="test-user-1")


# ── Initialization ──────────────────────────────────────────

class TestAgentInit:
    def test_initial_state_is_idle(self, agent):
        assert agent.state == ConversationState.IDLE

    def test_initial_context_is_empty(self, agent):
        assert agent.context == {}

    def test_initial_messages_is_empty(self, agent):
        assert agent.messages == []

    def test_initial_plan_is_none(self, agent):
        assert agent.plan is None


# ── start_conversation ──────────────────────────────────────

class TestStartConversation:
    @pytest.mark.asyncio
    async def test_health_goal_transitions_to_gathering_timeline(self, agent):
        result = await agent.start_conversation("I want to lose weight for a wedding")
        assert agent.state == ConversationState.GATHERING_TIMELINE

    @pytest.mark.asyncio
    async def test_health_goal_stores_context(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        assert "lose weight" in agent.context["goal"].lower()

    @pytest.mark.asyncio
    async def test_health_goal_returns_message(self, agent):
        result = await agent.start_conversation("I want to lose weight for a wedding")
        assert result["message"]  # non-empty
        assert result["state"] == ConversationState.GATHERING_TIMELINE

    @pytest.mark.asyncio
    async def test_non_fitness_goal_stays_idle(self, agent):
        result = await agent.start_conversation("I want to learn guitar")
        assert agent.state == ConversationState.IDLE
        assert "health" in result["message"].lower() or "fitness" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_messages_recorded(self, agent):
        await agent.start_conversation("I want to lose weight")
        assert len(agent.messages) == 2  # user + assistant
        assert agent.messages[0]["role"] == "user"
        assert agent.messages[1]["role"] == "assistant"


# ── State Machine Transitions ──────────────────────────────

class TestStateMachine:
    @pytest.mark.asyncio
    async def test_timeline_to_current_state(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        result = await agent.process_message("March 15th")
        assert agent.state == ConversationState.GATHERING_CURRENT_STATE
        assert agent.context["timeline"] == "March 15th"

    @pytest.mark.asyncio
    async def test_current_state_to_target(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        result = await agent.process_message("85 kg")
        assert agent.state == ConversationState.GATHERING_TARGET
        assert agent.context["current_state"] == "85 kg"

    @pytest.mark.asyncio
    async def test_target_to_preferences(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        result = await agent.process_message("75 kg")
        assert agent.state == ConversationState.GATHERING_PREFERENCES
        assert agent.context["target"] == "75 kg"

    @pytest.mark.asyncio
    async def test_suggest_target_to_preferences(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        result = await agent.process_message("Suggest one")
        assert agent.state == ConversationState.GATHERING_PREFERENCES

    @pytest.mark.asyncio
    async def test_preferences_to_awaiting_confirmation(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        result = await agent.process_message("Gym and diet")
        assert agent.state == ConversationState.AWAITING_CONFIRMATION
        assert agent.context["preferences"] == "Gym and diet"
        assert agent.plan is not None
        assert result.get("plan") is not None

    @pytest.mark.asyncio
    async def test_confirmation_yes_transitions_to_confirmed(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        await agent.process_message("Gym and diet")
        result = await agent.process_message("Looks good!")
        assert agent.state == ConversationState.CONFIRMED

    @pytest.mark.asyncio
    async def test_confirmation_no_stays_awaiting(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        await agent.process_message("Gym and diet")
        result = await agent.process_message("Can we change week 3?")
        assert agent.state == ConversationState.AWAITING_CONFIRMATION  # stays

    @pytest.mark.asyncio
    async def test_confirmed_agent_rejects_further_messages(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        await agent.process_message("Gym and diet")
        await agent.process_message("Looks good!")
        result = await agent.process_message("Hello?")
        assert "completed" in result["message"].lower() or "new" in result["message"].lower()


# ── Full Conversation Flow ──────────────────────────────────

class TestFullConversation:
    """The exact wedding weight-loss scenario from the acceptance criteria."""

    @pytest.mark.asyncio
    async def test_wedding_weight_loss_flow(self, agent):
        # Step 1: User states goal
        r1 = await agent.start_conversation("I want to lose weight for a wedding")
        assert agent.state == ConversationState.GATHERING_TIMELINE

        # Step 2: User gives timeline
        r2 = await agent.process_message("March 15th")
        assert agent.state == ConversationState.GATHERING_CURRENT_STATE

        # Step 3: User gives current weight
        r3 = await agent.process_message("85 kg")
        assert agent.state == ConversationState.GATHERING_TARGET

        # Step 4: User asks for suggestion
        r4 = await agent.process_message("Suggest one")
        assert agent.state == ConversationState.GATHERING_PREFERENCES

        # Step 5: User gives preferences
        r5 = await agent.process_message("Gym and diet")
        assert agent.state == ConversationState.AWAITING_CONFIRMATION
        assert agent.plan is not None
        assert len(agent.plan) == 6  # 6 milestones

        # Step 6: User confirms
        r6 = await agent.process_message("Looks good!")
        assert agent.state == ConversationState.CONFIRMED

    @pytest.mark.asyncio
    async def test_plan_has_6_milestones_with_tasks(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        await agent.process_message("Gym and diet")

        assert len(agent.plan) == 6
        for milestone in agent.plan:
            assert milestone.week >= 1
            assert milestone.title
            assert len(milestone.tasks) >= 3  # at least 3 tasks per milestone


# ── Serialization ───────────────────────────────────────────

class TestSerialization:
    @pytest.mark.asyncio
    async def test_to_dict_and_from_dict_roundtrip(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")

        data = agent.to_dict()
        restored = GoalPlannerAgent.from_dict(data)

        assert restored.state == agent.state
        assert restored.context == agent.context
        assert restored.user_id == agent.user_id
        assert len(restored.messages) == len(agent.messages)

    @pytest.mark.asyncio
    async def test_serialization_preserves_plan(self, agent):
        await agent.start_conversation("I want to lose weight for a wedding")
        await agent.process_message("March 15th")
        await agent.process_message("85 kg")
        await agent.process_message("75 kg")
        await agent.process_message("Gym and diet")

        data = agent.to_dict()
        restored = GoalPlannerAgent.from_dict(data)

        assert restored.plan is not None
        assert len(restored.plan) == len(agent.plan)
        assert restored.plan[0].title == agent.plan[0].title

    def test_to_dict_structure(self, agent):
        data = agent.to_dict()
        assert "conversation_id" in data
        assert "user_id" in data
        assert "state" in data
        assert "context" in data
        assert "messages" in data


# ── Fallback Behavior ──────────────────────────────────────

class TestFallbacks:
    def test_fallback_response_for_each_state(self, agent):
        for state in [
            ConversationState.GATHERING_TIMELINE,
            ConversationState.GATHERING_CURRENT_STATE,
            ConversationState.GATHERING_TARGET,
            ConversationState.GATHERING_PREFERENCES,
        ]:
            agent.state = state
            resp = agent._fallback_response()
            assert isinstance(resp, str)
            assert len(resp) > 10

    def test_fallback_plan_has_6_milestones(self, agent):
        plan = agent._fallback_plan()
        assert len(plan) == 6
        for m in plan:
            assert isinstance(m, PlanMilestone)
            assert m.week >= 1
            assert len(m.tasks) >= 3

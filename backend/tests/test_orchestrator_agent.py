"""Unit tests for OrchestratorAgent routing modes."""

from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import OrchestratorIntent, OrchestratorMessageRequest


def test_deterministic_route_start_goal_default():
    agent = OrchestratorAgent(use_langgraph=False)
    decision = agent.decide(
        OrchestratorMessageRequest(message="I want to lose weight")
    )
    assert decision.intent == OrchestratorIntent.START_GOAL
    assert decision.route == "goals.start"


def test_deterministic_route_list_tasks_phrase():
    agent = OrchestratorAgent(use_langgraph=False)
    decision = agent.decide(
        OrchestratorMessageRequest(message="show tasks for today")
    )
    assert decision.intent == OrchestratorIntent.LIST_TASKS
    assert decision.route == "scheduler.tasks"


def test_langgraph_flagged_mode_keeps_same_routing():
    agent = OrchestratorAgent(use_langgraph=True)
    decision = agent.decide(
        OrchestratorMessageRequest(message="show tasks for today")
    )
    assert decision.intent == OrchestratorIntent.LIST_TASKS
    assert decision.route == "scheduler.tasks"


def test_reschedule_with_event_id_routes_scheduler_suggest():
    agent = OrchestratorAgent(use_langgraph=True)
    decision = agent.decide(
        OrchestratorMessageRequest(
            message="please reschedule this",
            event_id="11111111-1111-1111-1111-111111111111",
        )
    )
    assert decision.intent == OrchestratorIntent.SUGGEST_RESCHEDULE
    assert decision.route == "scheduler.suggest"


def test_voice_action_routes_voice_create_session():
    agent = OrchestratorAgent(use_langgraph=False)
    decision = agent.decide(
        OrchestratorMessageRequest(
            voice_action="create_session",
            message="",
        )
    )
    assert decision.intent == OrchestratorIntent.VOICE_CREATE_SESSION
    assert decision.route == "voice.session.create"

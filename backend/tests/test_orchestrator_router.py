"""Tests for Orchestrator Router endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.schemas import (
    ConversationState,
    GoalConversationResponse,
    SchedulerApplyResponse,
    SchedulerSuggestResponse,
    TaskState,
)


@pytest.fixture()
def patch_orchestrator_delegates(monkeypatch):
    from app.routers import orchestrator as orch_router

    fake_goal_start = GoalConversationResponse(
        conversation_id="conv-123",
        state=ConversationState.GATHERING_TIMELINE,
        message="When is your event date?",
        suggested_action=None,
        plan=None,
        goal_id=None,
    )
    fake_goal_continue = GoalConversationResponse(
        conversation_id="conv-123",
        state=ConversationState.GATHERING_CURRENT_STATE,
        message="What is your current weight?",
        suggested_action=None,
        plan=None,
        goal_id=None,
    )
    fake_suggest = SchedulerSuggestResponse(
        event_id="11111111-1111-1111-1111-111111111111",
        task_title="Gym",
        suggestions=[],
        skip_option=True,
        ai_message="I can move this to later today.",
    )
    fake_apply = SchedulerApplyResponse(
        event_id="11111111-1111-1111-1111-111111111111",
        action="skip",
        new_state=TaskState.MISSED,
        message="Task skipped.",
    )

    monkeypatch.setattr(
        orch_router, "start_goal", AsyncMock(return_value=fake_goal_start)
    )
    monkeypatch.setattr(
        orch_router, "respond_to_goal", AsyncMock(return_value=fake_goal_continue)
    )
    monkeypatch.setattr(
        orch_router,
        "list_tasks_for_timeline",
        AsyncMock(return_value={"tasks": [{"id": "task-1"}, {"id": "task-2"}]}),
    )
    monkeypatch.setattr(
        orch_router, "suggest_reschedule", AsyncMock(return_value=fake_suggest)
    )
    monkeypatch.setattr(
        orch_router, "apply_reschedule", AsyncMock(return_value=fake_apply)
    )

    monkeypatch.setattr(
        orch_router,
        "voice_create_session",
        AsyncMock(
            return_value=type(
                "VoiceCreateResp",
                (),
                {"model_dump": lambda self, mode="json": {"session_id": "voice-s-1"}},
            )()
        ),
    )
    monkeypatch.setattr(
        orch_router,
        "voice_save_message",
        AsyncMock(
            return_value=type(
                "VoiceSaveResp",
                (),
                {
                    "model_dump": lambda self, mode="json": {
                        "message_id": "m-1",
                        "status": "saved",
                    }
                },
            )()
        ),
    )
    monkeypatch.setattr(
        orch_router,
        "voice_get_session_messages",
        AsyncMock(
            return_value=type(
                "VoiceGetResp",
                (),
                {
                    "model_dump": lambda self, mode="json": {
                        "session_id": "voice-s-1",
                        "messages": [],
                    }
                },
            )()
        ),
    )
    monkeypatch.setattr(
        orch_router,
        "voice_process_intent",
        AsyncMock(
            return_value=type(
                "VoiceIntentResp",
                (),
                {
                    "model_dump": lambda self, mode="json": {
                        "function_call_id": "fc-1",
                        "result": "ok",
                    }
                },
            )()
        ),
    )
    monkeypatch.setattr(
        orch_router,
        "voice_close_session",
        AsyncMock(
            return_value=type(
                "VoiceCloseResp",
                (),
                {
                    "model_dump": lambda self, mode="json": {
                        "session_id": "voice-s-1",
                        "status": "closed",
                    }
                },
            )()
        ),
    )


class TestOrchestratorRouter:
    def test_orchestrator_mode_endpoint(self, app_client):
        resp = app_client.get("/orchestrator/mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] in {"deterministic", "langgraph"}
        assert isinstance(data["use_langgraph_orchestrator"], bool)

    def test_start_goal_route(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "user_id": "test-user-1",
                "message": "I want to lose weight for my wedding",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "START_GOAL"
        assert data["route"] == "goals.start"
        assert data["conversation_id"]
        assert data["goal_state"] == ConversationState.GATHERING_TIMELINE

    def test_continue_goal_route(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "conversation_id": "conv-123",
                "message": "March 15th",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "CONTINUE_GOAL"
        assert data["route"] == "goals.respond"

    def test_list_tasks_route(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "message": "show tasks for today",
                "user_id": "a1000000-0000-0000-0000-000000000001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "LIST_TASKS"
        assert data["route"] == "scheduler.tasks"
        assert "scheduler_payload" in data
        assert len(data["scheduler_payload"]["tasks"]) == 2

    def test_suggest_requires_event_id(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "message": "reschedule this task please",
            },
        )
        # Falls back to START_GOAL because no event_id/uuid found
        assert resp.status_code == 200
        assert resp.json()["intent"] == "START_GOAL"

    def test_suggest_reschedule_route(self, app_client, patch_orchestrator_delegates):
        fake_id = "11111111-1111-1111-1111-111111111111"
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "message": "please reschedule this",
                "event_id": fake_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "SUGGEST_RESCHEDULE"
        assert data["route"] == "scheduler.suggest"

    def test_apply_skip_with_explicit_action(
        self, app_client, patch_orchestrator_delegates
    ):
        fake_id = "11111111-1111-1111-1111-111111111111"
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "message": "skip this",
                "event_id": fake_id,
                "action": "skip",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "APPLY_RESCHEDULE"
        assert data["route"] == "scheduler.apply"
        assert data["scheduler_payload"]["new_state"] == "missed"

    def test_apply_reschedule_with_time_window(
        self, app_client, patch_orchestrator_delegates
    ):
        fake_id = "11111111-1111-1111-1111-111111111111"
        new_start = datetime.now(timezone.utc) + timedelta(hours=2)
        new_end = new_start + timedelta(hours=1)
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "message": "reschedule",
                "event_id": fake_id,
                "action": "reschedule",
                "new_start": new_start.isoformat(),
                "new_end": new_end.isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "APPLY_RESCHEDULE"
        assert data["route"] == "scheduler.apply"

    def test_voice_create_session_route(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "voice_action": "create_session",
                "user_id": "a1000000-0000-0000-0000-000000000001",
                "message": "",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "VOICE_CREATE_SESSION"
        assert data["route"] == "voice.session.create"
        assert data["voice_payload"]["session_id"] == "voice-s-1"

    def test_voice_process_intent_route(self, app_client, patch_orchestrator_delegates):
        resp = app_client.post(
            "/orchestrator/message",
            json={
                "voice_action": "process_intent",
                "session_id": "voice-s-1",
                "function_call_id": "fc-1",
                "function_name": "submit_goal_intent",
                "input": {"goal_statement": "run a marathon"},
                "message": "",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "VOICE_PROCESS_INTENT"
        assert data["route"] == "voice.intents.process"
        assert data["voice_payload"]["function_call_id"] == "fc-1"

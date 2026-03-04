"""
Flux Backend — Orchestrator Router

Unified entrypoint for message routing across agents.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import OrchestratorAgent
from app.config import settings
from app.conv_agent.router import (
    close_session as voice_close_session,
    create_session as voice_create_session,
    get_session_messages as voice_get_session_messages,
    process_intent as voice_process_intent,
    save_message as voice_save_message,
)
from app.conv_agent.schemas import (
    CreateSessionRequest,
    SaveMessageRequest,
    SubmitIntentRequest,
)
from app.models.schemas import (
    OrchestratorIntent,
    OrchestratorMessageRequest,
    OrchestratorMessageResponse,
    RespondRequest,
    SchedulerApplyRequest,
    SchedulerSuggestRequest,
    StartGoalRequest,
)
from app.models.schemas import ConversationState
from app.routers.goals import respond_to_goal, start_goal
from app.routers.scheduler import (
    DEMO_USER_ID,
    apply_reschedule,
    list_tasks_for_timeline,
    suggest_reschedule,
)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_orchestrator = OrchestratorAgent(
    use_langgraph=settings.use_langgraph_orchestrator
)


@router.get("/mode")
async def orchestrator_mode():
    """Return active orchestrator mode for debugging/demo visibility."""
    return {
        "mode": "langgraph" if settings.use_langgraph_orchestrator else "deterministic",
        "use_langgraph_orchestrator": settings.use_langgraph_orchestrator,
    }


@router.post("/message", response_model=OrchestratorMessageResponse)
async def orchestrate_message(body: OrchestratorMessageRequest):
    """
    Route an incoming user message to Goal Planner or Scheduler.

    Supports:
    - Goal start / continue
    - Task timeline fetch
    - Reschedule suggestion / apply
    """
    try:
        decision = _orchestrator.decide(body)
        user_id = body.user_id or DEMO_USER_ID

        if decision.intent == OrchestratorIntent.VOICE_CREATE_SESSION:
            payload = await voice_create_session(CreateSessionRequest(user_id=user_id))
            data = payload.model_dump(mode="json")
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message="Voice session created.",
                voice_payload=data,
            )

        if decision.intent == OrchestratorIntent.VOICE_SAVE_MESSAGE:
            if not body.session_id:
                raise HTTPException(status_code=400, detail="session_id required for voice save_message")
            if not body.role:
                raise HTTPException(status_code=400, detail="role required for voice save_message")
            payload = await voice_save_message(
                SaveMessageRequest(
                    session_id=body.session_id,
                    role=body.role,
                    content=body.message or "",
                )
            )
            data = payload.model_dump(mode="json")
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message="Voice transcript saved.",
                conversation_id=body.session_id,
                voice_payload=data,
            )

        if decision.intent == OrchestratorIntent.VOICE_GET_MESSAGES:
            if not body.session_id:
                raise HTTPException(status_code=400, detail="session_id required for voice get_messages")
            payload = await voice_get_session_messages(body.session_id)
            data = payload.model_dump(mode="json")
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message="Voice messages fetched.",
                conversation_id=body.session_id,
                voice_payload=data,
            )

        if decision.intent == OrchestratorIntent.VOICE_PROCESS_INTENT:
            if not body.session_id:
                raise HTTPException(status_code=400, detail="session_id required for voice process_intent")
            if not body.function_call_id:
                raise HTTPException(status_code=400, detail="function_call_id required for voice process_intent")
            if not body.function_name:
                raise HTTPException(status_code=400, detail="function_name required for voice process_intent")

            payload = await voice_process_intent(
                SubmitIntentRequest(
                    session_id=body.session_id,
                    function_call_id=body.function_call_id,
                    function_name=body.function_name,
                    input=body.input or {},
                )
            )
            data = payload.model_dump(mode="json")
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message="Voice intent processed.",
                conversation_id=body.session_id,
                voice_payload=data,
            )

        if decision.intent == OrchestratorIntent.VOICE_CLOSE_SESSION:
            if not body.session_id:
                raise HTTPException(status_code=400, detail="session_id required for voice close_session")
            payload = await voice_close_session(body.session_id)
            data = payload.model_dump(mode="json")
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message="Voice session closed.",
                conversation_id=body.session_id,
                voice_payload=data,
            )

        if decision.intent == OrchestratorIntent.START_GOAL:
            goal = await start_goal(
                StartGoalRequest(user_id=user_id, message=body.message)
            )
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message=goal.message,
                conversation_id=goal.conversation_id,
                goal_state=goal.state,
                goal_id=goal.goal_id,
                suggested_action=goal.suggested_action,
                proposed_plan=goal.plan,
                requires_user_action=goal.state == ConversationState.AWAITING_CONFIRMATION,
            )

        if decision.intent == OrchestratorIntent.CONTINUE_GOAL:
            if not body.conversation_id:
                raise HTTPException(status_code=400, detail="conversation_id required")
            goal = await respond_to_goal(
                body.conversation_id,
                RespondRequest(message=body.message),
            )
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message=goal.message,
                conversation_id=goal.conversation_id,
                goal_state=goal.state,
                goal_id=goal.goal_id,
                suggested_action=goal.suggested_action,
                proposed_plan=goal.plan,
                requires_user_action=goal.state == ConversationState.AWAITING_CONFIRMATION,
            )

        if decision.intent == OrchestratorIntent.LIST_TASKS:
            try:
                tasks_payload = await list_tasks_for_timeline(user_id=user_id)
            except Exception:
                tasks_payload = {"tasks": []}

            task_count = len(tasks_payload.get("tasks", []))
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message=f"Found {task_count} task(s) in your timeline.",
                scheduler_payload=tasks_payload,
            )

        if decision.intent == OrchestratorIntent.SUGGEST_RESCHEDULE:
            event_id = body.event_id or _orchestrator.extract_event_id(body.message.lower())
            if not event_id:
                raise HTTPException(status_code=400, detail="event_id required for reschedule suggestions")
            suggestion = await suggest_reschedule(
                SchedulerSuggestRequest(event_id=event_id)
            )
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message=suggestion.ai_message,
                scheduler_payload=suggestion.model_dump(mode="json"),
            )

        if decision.intent == OrchestratorIntent.APPLY_RESCHEDULE:
            event_id = body.event_id or _orchestrator.extract_event_id(body.message.lower())
            if not event_id:
                raise HTTPException(status_code=400, detail="event_id required for apply action")

            action = body.action
            if not action:
                action = "skip" if "skip" in body.message.lower() else "reschedule"

            applied = await apply_reschedule(
                SchedulerApplyRequest(
                    event_id=event_id,
                    action=action,
                    new_start=body.new_start,
                    new_end=body.new_end,
                )
            )
            return OrchestratorMessageResponse(
                intent=decision.intent,
                route=decision.route,
                message=applied.message,
                scheduler_payload=applied.model_dump(mode="json"),
            )

        return OrchestratorMessageResponse(
            intent=OrchestratorIntent.UNKNOWN,
            route="none",
            message="I couldn't determine the right route for that message.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {exc}") from exc

"""
Flux Backend — Goals Router

API endpoints for the Goal Planner agent conversation flow.

Endpoints:
  POST /goals/start         — Start a new goal conversation
  POST /goals/{id}/respond  — Send a message in an ongoing conversation
  GET  /goals/{id}          — Get conversation state (for reconnection)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.agents.goal_planner import GoalPlannerAgent
from app.models.schemas import (
    ConversationState,
    GoalConversationResponse,
    RespondRequest,
    StartGoalRequest,
)
from app.services import goal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["goals"])

# ── In-memory agent cache ──────────────────────────────────
# Maps conversation_id → GoalPlannerAgent
# In production this would be Redis or similar; fine for MVP.
_active_agents: dict[str, GoalPlannerAgent] = {}


# ── POST /goals/start ──────────────────────────────────────

@router.post("/start", response_model=GoalConversationResponse)
async def start_goal(body: StartGoalRequest):
    """
    Start a new goal-planning conversation.

    The user sends their initial goal statement. The agent responds with
    the first question to begin the empathetic context extraction flow.
    """
    try:
        # Create agent
        agent = GoalPlannerAgent(
            conversation_id="",  # will be set after DB insert
            user_id=body.user_id,
        )

        # Run the first turn
        result = await agent.start_conversation(body.message)

        # Persist conversation to DB
        try:
            conversation_id = goal_service.create_conversation(
                user_id=body.user_id,
                initial_state=agent.to_dict(),
            )
            agent.conversation_id = conversation_id

            # Save updated state (now with the real conversation_id)
            goal_service.update_conversation(conversation_id, agent.to_dict())
        except Exception as db_err:
            # DB might not be available yet — continue with in-memory only
            logger.warning(f"DB write failed (continuing in-memory): {db_err}")
            import uuid
            conversation_id = str(uuid.uuid4())
            agent.conversation_id = conversation_id

        # Cache agent in memory
        _active_agents[conversation_id] = agent

        return GoalConversationResponse(
            conversation_id=conversation_id,
            state=result["state"],
            message=result["message"],
            suggested_action=result.get("suggested_action"),
            plan=result.get("plan"),
            goal_id=None,
        )

    except Exception as e:
        logger.error(f"Failed to start goal conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /goals/{id}/respond ───────────────────────────────

@router.post("/{conversation_id}/respond", response_model=GoalConversationResponse)
async def respond_to_goal(conversation_id: str, body: RespondRequest):
    """
    Continue an ongoing goal-planning conversation.

    Send the user's response text. The agent will advance its state
    machine and return the next question, or the final plan.
    """
    # Try to get agent from memory cache
    agent = _active_agents.get(conversation_id)

    if not agent:
        # Try to restore from DB
        try:
            conv_data = goal_service.get_conversation(conversation_id)
            if not conv_data:
                raise HTTPException(status_code=404, detail="Conversation not found")

            import json
            stored_state = conv_data.get("messages")
            if isinstance(stored_state, str):
                stored_state = json.loads(stored_state)

            if isinstance(stored_state, dict) and "state" in stored_state:
                agent = GoalPlannerAgent.from_dict(stored_state)
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation state corrupted or not found",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to restore conversation: {e}")
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Process the user's message
    try:
        result = await agent.process_message(body.message)
    except Exception as e:
        logger.error(f"Agent processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

    goal_id = None

    # If the plan was confirmed, persist everything to DB
    if result["state"] == ConversationState.CONFIRMED and agent.plan:
        try:
            saved = goal_service.save_complete_plan(
                user_id=agent.user_id,
                conversation_id=conversation_id,
                agent_context=agent.context,
                milestones=agent.plan,
            )
            goal_id = saved["goal_id"]
            logger.info(f"Plan saved to DB: {saved}")
        except Exception as db_err:
            logger.warning(f"Failed to save plan to DB: {db_err}")
            # Don't fail the response — the plan is still in memory

    # Persist updated agent state
    try:
        goal_service.update_conversation(conversation_id, agent.to_dict())
    except Exception as db_err:
        logger.warning(f"Failed to update conversation in DB: {db_err}")

    # Keep agent in cache
    _active_agents[conversation_id] = agent

    return GoalConversationResponse(
        conversation_id=conversation_id,
        state=result["state"],
        message=result["message"],
        suggested_action=result.get("suggested_action"),
        plan=result.get("plan"),
        goal_id=goal_id,
    )


# ── GET /goals/{id} ────────────────────────────────────────

@router.get("/{conversation_id}", response_model=GoalConversationResponse)
async def get_goal_conversation(conversation_id: str):
    """
    Get the current state of a goal conversation.
    Useful for reconnecting after a page refresh.
    """
    agent = _active_agents.get(conversation_id)

    if not agent:
        try:
            conv_data = goal_service.get_conversation(conversation_id)
            if not conv_data:
                raise HTTPException(status_code=404, detail="Conversation not found")

            import json
            stored_state = conv_data.get("messages")
            if isinstance(stored_state, str):
                stored_state = json.loads(stored_state)

            if isinstance(stored_state, dict) and "state" in stored_state:
                agent = GoalPlannerAgent.from_dict(stored_state)
                _active_agents[conversation_id] = agent
            else:
                raise HTTPException(status_code=404, detail="Conversation not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to restore conversation: {e}")
            raise HTTPException(status_code=404, detail="Conversation not found")

    return GoalConversationResponse(
        conversation_id=conversation_id,
        state=agent.state,
        message=agent.messages[-1]["content"] if agent.messages else "",
        suggested_action=None,
        plan=[m for m in agent.plan] if agent.plan else None,
        goal_id=None,
    )

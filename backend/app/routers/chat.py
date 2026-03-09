"""
Flux Backend — Chat & Account Router

Unified chat endpoint for onboarding (and later goal chat). Account endpoint
for user profile and onboarding status. Aligned to FE-4 contract.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.goal_planner import GoalPlannerAgent
from app.agents.onboarding_agent import OnboardingAgent
from app.auth import get_current_user
from app.models.schemas import ConversationState
from app.services import goal_service, onboarding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# In-memory onboarding agents keyed by user_id
_onboarding_agents: dict[str, OnboardingAgent] = {}

# In-memory goal planner agents keyed by user_id (one active goal conversation per user)
_goal_agents: dict[str, GoalPlannerAgent] = {}


def get_or_create_onboarding_agent(user_id: str) -> OnboardingAgent:
    if user_id not in _onboarding_agents:
        _onboarding_agents[user_id] = OnboardingAgent()
    return _onboarding_agents[user_id]


def _goal_sources_to_list(raw: list[dict] | None) -> list[dict]:
    """Convert agent sources (title, source) to response shape (title, url)."""
    if not raw:
        return []
    return [{"title": s.get("title", ""), "url": s.get("source", "")} for s in raw]


def _plan_to_list(plan: list | None) -> list[dict] | None:
    """Serialize plan milestones for JSON response."""
    if not plan:
        return None
    return [m.model_dump() if hasattr(m, "model_dump") else m for m in plan]


class ChatMessageRequest(BaseModel):
    message: str = Field(
        default="", description="User message; empty string for resume."
    )


# ── POST /api/v1/chat/message ─────────────────────────────────


@router.post("/chat/message")
async def chat_message(
    body: ChatMessageRequest,
    user: dict = Depends(get_current_user),
):
    """
    Single chat endpoint for onboarding and (later) goal chat.
    FE-4 contract: returns { message, state?, progress?, is_complete?, profile? }.
    """
    user_id = user["sub"]
    message = (body.message or "").strip()

    onboarded = await onboarding_service.is_user_onboarded(user_id)
    if not onboarded:
        agent = get_or_create_onboarding_agent(user_id)
        result = await agent.process_message(message)

        if result.get("is_complete"):
            await onboarding_service.save_profile(user_id, result["profile"])
            _onboarding_agents.pop(user_id, None)

        return {
            "message": result["message"],
            "state": result.get("state"),
            "progress": result.get("progress"),
            "is_complete": result.get("is_complete", False),
            "profile": result.get("profile"),
            "sources": [],
        }

    # Onboarded: route to GoalPlannerAgent
    _NEW_GOAL_KEYWORDS = (
        "new goal",
        "start over",
        "reset",
        "another goal",
        "new conversation",
    )
    if message.lower().strip() in _NEW_GOAL_KEYWORDS or any(
        message.lower().startswith(kw) for kw in _NEW_GOAL_KEYWORDS
    ):
        _goal_agents.pop(user_id, None)
        return {
            "message": "Sure! What goal would you like to work on?",
            "state": None,
            "progress": None,
            "is_complete": False,
            "profile": None,
            "proposed_plan": None,
            "sources": [],
        }

    agent = _goal_agents.get(user_id)
    if not agent:
        conversation_id = str(uuid.uuid4())
        agent = GoalPlannerAgent(conversation_id=conversation_id, user_id=user_id)
        _goal_agents[user_id] = agent
        try:
            result = await agent.start_conversation(message)
        except Exception as e:
            logger.error("Goal agent start_conversation failed: %s", e, exc_info=True)
            _goal_agents.pop(user_id, None)
            raise HTTPException(
                status_code=500, detail="Failed to start goal conversation"
            )
    else:
        try:
            result = await agent.process_message(message)
        except Exception as e:
            logger.error("Goal agent process_message failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to process message")

    state_value = (
        result["state"].value
        if isinstance(result["state"], ConversationState)
        else result["state"]
    )
    sources = (
        _goal_sources_to_list(result.get("sources")) if result.get("sources") else []
    )

    if result["state"] == ConversationState.CONFIRMED and agent.plan:
        try:
            goal_service.save_complete_plan(
                user_id=user_id,
                conversation_id=agent.conversation_id,
                agent_context=agent.context,
                milestones=agent.plan,
            )
        except Exception as db_err:
            logger.warning("Failed to save plan to DB: %s", db_err)
        _goal_agents.pop(user_id, None)

    return {
        "message": result["message"],
        "state": state_value,
        "progress": None,
        "is_complete": False,
        "profile": None,
        "proposed_plan": _plan_to_list(result.get("plan")),
        "sources": sources,
    }


# ── GET /api/v1/account/me ─────────────────────────────────────


@router.get("/account/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Return current user with onboarded, and when not onboarded also
    current_step and total_steps for the frontend.
    """
    user_id = user["sub"]
    user_data = await onboarding_service.get_user_with_onboarding_status(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    agent = _onboarding_agents.get(user_id)
    if user_data.get("onboarded"):
        return {
            **user_data,
            "current_step": 7,
            "total_steps": 7,
        }
    return {
        **user_data,
        "current_step": agent.current_step_index if agent else 0,
        "total_steps": 7,
    }

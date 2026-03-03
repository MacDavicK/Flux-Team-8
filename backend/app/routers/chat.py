"""
Flux Backend — Chat & Account Router

Unified chat endpoint for onboarding (and later goal chat). Account endpoint
for user profile and onboarding status. Aligned to FE-4 contract.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.onboarding_agent import OnboardingAgent
from app.auth import get_current_user
from app.services import onboarding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# In-memory onboarding agents keyed by user_id
_onboarding_agents: dict[str, OnboardingAgent] = {}


def get_or_create_onboarding_agent(user_id: str) -> OnboardingAgent:
    if user_id not in _onboarding_agents:
        _onboarding_agents[user_id] = OnboardingAgent()
    return _onboarding_agents[user_id]


class ChatMessageRequest(BaseModel):
    message: str = Field(default="", description="User message; empty string for resume.")


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

    # Already onboarded — respond briefly; goal chat can be added here later
    return {
        "message": "You're all set! Start a goal from the home screen when you're ready.",
        "state": None,
        "progress": 1.0,
        "is_complete": False,
        "profile": None,
        "sources": [],
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

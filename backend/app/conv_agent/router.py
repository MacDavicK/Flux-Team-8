"""
Flux Conv Agent -- Router

REST-only control plane for the voice conversational agent.
Handles session lifecycle, message persistence, and intent processing.

Endpoints:
  POST   /api/v1/voice/session                    -- Create a new voice session
  POST   /api/v1/voice/messages                   -- Save a transcript message
  GET    /api/v1/voice/sessions/{id}/messages      -- Get session transcript
  POST   /api/v1/voice/intents                    -- Process a function-call intent
  DELETE /api/v1/voice/session/{id}                -- Close a voice session
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.conv_agent.schemas import (
    CloseSessionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetMessagesResponse,
    IntentResultResponse,
    MessageRecord,
    SaveMessageRequest,
    SaveMessageResponse,
    SubmitIntentRequest,
)
from app.conv_agent import voice_service
from app.conv_agent.intent_handler import handle_intent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


# -- POST /api/v1/voice/session ----------------------------------------------


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(body: CreateSessionRequest):
    """
    Start a new voice session.

    Creates a conversation row, mints a short-lived Deepgram token,
    loads the system prompt with user context, and returns everything
    the frontend needs to connect directly to Deepgram.
    """
    try:
        result = await voice_service.build_session_config(body.user_id)
        return CreateSessionResponse(**result)
    except Exception as exc:
        logger.error("Failed to create voice session: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create voice session")


# -- POST /api/v1/voice/messages ---------------------------------------------


@router.post("/messages", response_model=SaveMessageResponse)
async def save_message(body: SaveMessageRequest):
    """
    Persist a single transcript message (fire-and-forget from frontend).

    Called by the frontend whenever Deepgram emits a ConversationText event.
    Must not block the voice flow -- errors are logged but return 200.
    """
    try:
        message_id = await voice_service.save_message(
            session_id=body.session_id,
            role=body.role,
            content=body.content,
        )
        return SaveMessageResponse(message_id=message_id)
    except Exception as exc:
        logger.error("Failed to save message: %s", exc, exc_info=True)
        # Return a success response anyway -- fire-and-forget semantics
        return SaveMessageResponse(message_id="error", status="failed")


# -- GET /api/v1/voice/sessions/{session_id}/messages ------------------------


@router.get(
    "/sessions/{session_id}/messages",
    response_model=GetMessagesResponse,
)
async def get_session_messages(session_id: str):
    """
    Retrieve the full transcript for a voice session.

    Returns messages ordered chronologically.
    """
    try:
        messages = await voice_service.get_messages(session_id)
        return GetMessagesResponse(
            session_id=session_id,
            messages=[MessageRecord(**m) for m in messages],
        )
    except Exception as exc:
        logger.error("Failed to get messages: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


# -- POST /api/v1/voice/intents ----------------------------------------------


@router.post("/intents", response_model=IntentResultResponse)
async def process_intent(body: SubmitIntentRequest):
    """
    Process a Deepgram FunctionCallRequest.

    The frontend forwards function calls from Deepgram here.
    This routes to the appropriate backend service (goal, task,
    reschedule) and returns a text result for the agent to speak.
    """
    try:
        result_text = await handle_intent(
            function_name=body.function_name,
            params=body.input,
            session_id=body.session_id,
        )
        return IntentResultResponse(
            function_call_id=body.function_call_id,
            result=result_text,
        )
    except Exception as exc:
        logger.error("Failed to process intent: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process intent")


# -- DELETE /api/v1/voice/session/{session_id} -------------------------------


@router.delete("/session/{session_id}", response_model=CloseSessionResponse)
async def close_session(session_id: str):
    """
    Close a voice session.

    Marks the conversation as ended and returns the message count.
    """
    try:
        message_count = await voice_service.close_session(session_id)
        return CloseSessionResponse(
            session_id=session_id,
            status="closed",
            message_count=message_count,
        )
    except Exception as exc:
        logger.error("Failed to close session: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to close session")

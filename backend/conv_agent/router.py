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
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.config import settings as app_settings
from conv_agent.schemas import (
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
from conv_agent import voice_service
from conv_agent.intent_handler import handle_intent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


async def _auth_user_from_bearer_token(request: Request) -> Optional[dict]:
    """
    If the request has Authorization: Bearer <jwt>, call Supabase Auth and return
    the full user dict (id, email, user_metadata, ...). Otherwise return None.
    Uses async httpx so the request is not used from another thread (ASGI-safe).
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    url = f"{app_settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": app_settings.supabase_key,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        logger.debug("Could not resolve user from Bearer token: %s", e)
        return None


def _ensure_public_user_from_auth(auth_user: dict) -> None:
    """
    Ensure the auth user exists in public.users (sync with Supabase Auth).
    Idempotent: if the row already exists (e.g. from trigger), we do nothing.
    Uses the admin client (service role key) so the insert bypasses RLS.
    """
    from app.database import get_supabase_admin_client
    user_id = auth_user.get("id")
    email = auth_user.get("email") or ""
    if not user_id or not email:
        return
    meta = auth_user.get("user_metadata") or {}
    name = meta.get("name") or meta.get("full_name") or ""
    profile = {"name": name} if name else None
    payload = {"id": user_id, "email": email}
    if profile is not None:
        payload["profile"] = profile
    try:
        supabase = get_supabase_admin_client()
        supabase.table("users").insert(payload).execute()
    except Exception as e:
        err_str = str(e).lower()
        if "duplicate" in err_str or "unique" in err_str or "23505" in err_str:
            logger.debug("public.users row already exists for %s", user_id)
            return
        logger.warning("Could not ensure public user from auth: %s", e)
        raise


# -- POST /api/v1/voice/session ----------------------------------------------


@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: Request, body: CreateSessionRequest):
    """
    Start a new voice session.

    Creates a conversation row, mints a short-lived Deepgram token,
    loads the system prompt with user context, and returns everything
    the frontend needs to connect directly to Deepgram.

    User identity: if the request includes a valid Authorization Bearer token
    (Supabase JWT), the user_id is taken from the token. Otherwise body.user_id
    is used (e.g. for tests or legacy clients).

    If the user exists in Supabase Auth but not in public.users (e.g. trigger
    didn't run), we sync them into public.users and retry.
    """
    auth_user = await _auth_user_from_bearer_token(request)
    user_id = (auth_user.get("id") if auth_user else None) or body.user_id
    try:
        result = await voice_service.build_session_config(user_id)
        return CreateSessionResponse(**result)
    except ValueError as exc:
        if "not found in the database" in str(exc) and auth_user:
            _ensure_public_user_from_auth(auth_user)
            try:
                result = await voice_service.build_session_config(user_id)
                return CreateSessionResponse(**result)
            except Exception as retry_exc:
                logger.error("Failed to create voice session after sync: %s", retry_exc, exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to create voice session")
        logger.error("Failed to create voice session: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create voice session")
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

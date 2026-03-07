"""
Flux Conv Agent -- Pydantic Schemas

Request and response models for the Voice Conversational Agent endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# -- Request Models ----------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Body for POST /api/v1/voice/session -- start a new voice session."""
    user_id: str = Field(..., description="UUID of the user starting the session")


class SaveMessageRequest(BaseModel):
    """Body for POST /api/v1/voice/messages -- persist a transcript turn."""
    session_id: str = Field(..., description="UUID of the voice session (conversation_id)")
    role: str = Field(..., description="Message role: user, assistant, system, or function")
    content: str = Field(..., description="Transcript text content")


class SubmitIntentRequest(BaseModel):
    """Body for POST /api/v1/voice/intents -- forward a Deepgram function call."""
    session_id: str = Field(..., description="UUID of the voice session")
    function_call_id: str = Field(..., description="Deepgram function call ID (e.g. fc_123)")
    function_name: str = Field(..., description="Name of the called function/intent")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters extracted by the voice agent LLM",
    )


# -- Response Models ---------------------------------------------------------


class FunctionConfig(BaseModel):
    """A single Deepgram function definition sent to the voice agent."""
    name: str
    description: str
    parameters: dict[str, Any]


class SessionConfig(BaseModel):
    """Configuration payload returned when a voice session is created."""
    system_prompt: str
    functions: list[FunctionConfig]
    voice_model: str
    listen_model: str
    llm_model: str
    greeting: str = "Hey! What can I help you with today?"


class CreateSessionResponse(BaseModel):
    """Response for POST /api/v1/voice/session."""
    session_id: str
    deepgram_token: str
    config: SessionConfig


class SaveMessageResponse(BaseModel):
    """Response for POST /api/v1/voice/messages."""
    message_id: str
    status: str = "saved"


class MessageRecord(BaseModel):
    """A single message in a session transcript."""
    id: str
    role: str
    content: str
    created_at: datetime


class GetMessagesResponse(BaseModel):
    """Response for GET /api/v1/voice/sessions/{session_id}/messages."""
    session_id: str
    messages: list[MessageRecord]


class IntentResultResponse(BaseModel):
    """Response for POST /api/v1/voice/intents."""
    function_call_id: str
    result: str


class CloseSessionResponse(BaseModel):
    """Response for DELETE /api/v1/voice/session/{session_id}."""
    session_id: str
    status: str = "closed"
    message_count: int

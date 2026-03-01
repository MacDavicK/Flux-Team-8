"""Conversation DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from dao_service.schemas.base import BaseSchema

CONTEXT_TYPE_VALUES = {"onboarding", "goal", "task", "reschedule", "voice"}


class ConversationBase(BaseSchema):
    langgraph_thread_id: str = Field(..., min_length=1)
    context_type: str
    last_message_at: Optional[datetime] = None

    @field_validator("context_type")
    @classmethod
    def validate_context_type(cls, value: str) -> str:
        if value not in CONTEXT_TYPE_VALUES:
            raise ValueError(f"context_type must be one of: {sorted(CONTEXT_TYPE_VALUES)}")
        return value


class ConversationCreateDTO(ConversationBase):
    user_id: UUID
    voice_session_id: Optional[str] = None


class ConversationUpdateDTO(BaseSchema):
    context_type: Optional[str] = None
    last_message_at: Optional[datetime] = None

    @field_validator("context_type")
    @classmethod
    def validate_context_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in CONTEXT_TYPE_VALUES:
            raise ValueError(f"context_type must be one of: {sorted(CONTEXT_TYPE_VALUES)}")
        return value


class VoiceConversationUpdateDTO(BaseModel):
    """For PATCH /conversations/{id}/voice -- voice session close."""

    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    extracted_intent: Optional[str] = None
    intent_payload: Optional[dict] = None
    linked_goal_id: Optional[UUID] = None
    linked_task_id: Optional[UUID] = None


class ConversationDTO(ConversationBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    voice_session_id: Optional[str] = None
    extracted_intent: Optional[str] = None
    intent_payload: Optional[dict] = None
    linked_goal_id: Optional[UUID] = None
    linked_task_id: Optional[UUID] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

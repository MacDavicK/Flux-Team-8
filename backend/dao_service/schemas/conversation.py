"""Conversation DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from dao_service.schemas.base import BaseSchema

CONTEXT_TYPE_VALUES = {"onboarding", "goal", "task", "reschedule"}


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


class ConversationUpdateDTO(BaseSchema):
    context_type: Optional[str] = None
    last_message_at: Optional[datetime] = None

    @field_validator("context_type")
    @classmethod
    def validate_context_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in CONTEXT_TYPE_VALUES:
            raise ValueError(f"context_type must be one of: {sorted(CONTEXT_TYPE_VALUES)}")
        return value


class ConversationDTO(ConversationBase):
    id: UUID
    user_id: UUID
    created_at: datetime

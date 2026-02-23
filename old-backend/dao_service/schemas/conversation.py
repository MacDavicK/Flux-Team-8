"""Conversation DTOs."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class ConversationBase(BaseSchema):
    messages: Optional[List] = Field(default_factory=list)
    status: str = "open"


class ConversationCreateDTO(ConversationBase):
    user_id: UUID
    goal_id: UUID


class ConversationUpdateDTO(BaseSchema):
    messages: Optional[List] = None
    status: Optional[str] = None


class ConversationDTO(ConversationBase):
    id: UUID
    user_id: UUID
    goal_id: UUID
    created_at: datetime

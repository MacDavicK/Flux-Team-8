"""Milestone DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class MilestoneBase(BaseSchema):
    week_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "pending"


class MilestoneCreateDTO(MilestoneBase):
    goal_id: UUID


class MilestoneUpdateDTO(BaseSchema):
    week_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = None


class MilestoneDTO(MilestoneBase):
    id: UUID
    goal_id: UUID
    created_at: datetime

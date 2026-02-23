"""Goal DTOs."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from dao_service.schemas.base import BaseSchema

GOAL_STATUS_VALUES = {"active", "completed", "abandoned", "pipeline"}


class GoalBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    class_tags: Optional[List[str]] = None
    status: str = "active"
    parent_goal_id: Optional[UUID] = None
    pipeline_order: Optional[int] = None
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    target_weeks: int = Field(default=6, ge=1)
    plan_json: Optional[dict] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in GOAL_STATUS_VALUES:
            raise ValueError(f"status must be one of: {sorted(GOAL_STATUS_VALUES)}")
        return value


class GoalCreateDTO(GoalBase):
    user_id: UUID


class GoalUpdateDTO(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    class_tags: Optional[List[str]] = None
    status: Optional[str] = None
    parent_goal_id: Optional[UUID] = None
    pipeline_order: Optional[int] = None
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    target_weeks: Optional[int] = Field(default=None, ge=1)
    plan_json: Optional[dict] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in GOAL_STATUS_VALUES:
            raise ValueError(f"status must be one of: {sorted(GOAL_STATUS_VALUES)}")
        return value


class GoalDTO(GoalBase):
    id: UUID
    user_id: UUID
    created_at: datetime

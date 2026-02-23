"""Task DTOs including specialized scheduler/observer schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from dao_service.schemas.base import BaseSchema

TASK_STATUS_VALUES = {"pending", "done", "missed", "rescheduled", "cancelled"}
TRIGGER_TYPE_VALUES = {"time", "location"}


class TaskBase(BaseSchema):
    """Shared task attributes."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "pending"
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    trigger_type: str = "time"
    location_trigger: Optional[str] = None
    reminder_sent_at: Optional[datetime] = None
    whatsapp_sent_at: Optional[datetime] = None
    call_sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    shared_with_goal_ids: Optional[List[UUID]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in TASK_STATUS_VALUES:
            raise ValueError(f"status must be one of: {sorted(TASK_STATUS_VALUES)}")
        return value

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger_type(cls, value: str) -> str:
        if value not in TRIGGER_TYPE_VALUES:
            raise ValueError(f"trigger_type must be one of: {sorted(TRIGGER_TYPE_VALUES)}")
        return value


class TaskCreateDTO(TaskBase):
    """For creation requests."""

    user_id: UUID
    goal_id: Optional[UUID] = None


class TaskUpdateDTO(BaseSchema):
    """For updates — all fields optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    trigger_type: Optional[str] = None
    location_trigger: Optional[str] = None
    reminder_sent_at: Optional[datetime] = None
    whatsapp_sent_at: Optional[datetime] = None
    call_sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    recurrence_rule: Optional[str] = None
    shared_with_goal_ids: Optional[List[UUID]] = None
    goal_id: Optional[UUID] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TASK_STATUS_VALUES:
            raise ValueError(f"status must be one of: {sorted(TASK_STATUS_VALUES)}")
        return value

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TRIGGER_TYPE_VALUES:
            raise ValueError(f"trigger_type must be one of: {sorted(TRIGGER_TYPE_VALUES)}")
        return value


class TaskDTO(TaskBase):
    """Complete response schema."""

    id: UUID
    user_id: UUID
    goal_id: Optional[UUID] = None
    created_at: datetime


# --- Specialized DTOs for Scheduler / Observer endpoints ---


class BulkUpdateStateRequest(BaseSchema):
    """Bulk status update request from Scheduler."""

    task_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    new_status: str

    @field_validator("new_status")
    @classmethod
    def validate_new_status(cls, value: str) -> str:
        if value not in TASK_STATUS_VALUES:
            raise ValueError(f"new_status must be one of: {sorted(TASK_STATUS_VALUES)}")
        return value


class BulkUpdateResponse(BaseSchema):
    """Response for bulk update operations."""

    updated_count: int


class TaskStatisticsDTO(BaseSchema):
    """Aggregated task statistics for Observer."""

    user_id: UUID
    total_tasks: int
    by_status: Dict[str, int]
    completion_rate: float

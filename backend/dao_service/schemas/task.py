"""Task DTOs including specialized scheduler/observer schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from dao_service.schemas.base import BaseSchema
from dao_service.schemas.enums import TaskPriority, TaskState, TriggerType


class TaskBase(BaseSchema):
    """Shared task attributes."""

    title: str = Field(..., min_length=1, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: TaskState = TaskState.SCHEDULED
    priority: TaskPriority = TaskPriority.STANDARD
    trigger_type: TriggerType = TriggerType.TIME
    is_recurring: bool = False

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v, info):
        if v and info.data.get("start_time") and v < info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class TaskCreateDTO(TaskBase):
    """For creation requests."""

    user_id: UUID
    goal_id: UUID
    milestone_id: Optional[UUID] = None


class TaskUpdateDTO(BaseSchema):
    """For updates — all fields optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: Optional[TaskState] = None
    priority: Optional[TaskPriority] = None
    trigger_type: Optional[TriggerType] = None
    is_recurring: Optional[bool] = None
    calendar_event_id: Optional[str] = None


class TaskDTO(TaskBase):
    """Complete response schema."""

    id: UUID
    user_id: UUID
    goal_id: UUID
    milestone_id: Optional[UUID] = None
    calendar_event_id: Optional[str] = None
    created_at: datetime


# --- Specialized DTOs for Scheduler / Observer endpoints ---


class BulkUpdateStateRequest(BaseSchema):
    """Bulk state update request from Scheduler."""

    task_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    new_state: TaskState


class BulkUpdateResponse(BaseSchema):
    """Response for bulk update operations."""

    updated_count: int


class CalendarEventUpdateRequest(BaseSchema):
    """Calendar event ID update from Scheduler."""

    calendar_event_id: str = Field(..., min_length=1, max_length=255)


class TaskStatisticsDTO(BaseSchema):
    """Aggregated task statistics for Observer."""

    user_id: UUID
    total_tasks: int
    by_state: Dict[str, int]
    completion_rate: float

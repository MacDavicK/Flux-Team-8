"""Goal DTOs."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class GoalBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None
    timeline: Optional[str] = None
    status: str = "active"


class GoalCreateDTO(GoalBase):
    user_id: UUID


class GoalUpdateDTO(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None


class GoalDTO(GoalBase):
    id: UUID
    user_id: UUID
    created_at: datetime


class MilestoneInGoalDTO(BaseSchema):
    """Inline milestone for GoalWithRelationsDTO."""

    id: UUID
    week_number: int
    title: str
    status: str
    created_at: datetime


class TaskInGoalDTO(BaseSchema):
    """Inline task for GoalWithRelationsDTO."""

    id: UUID
    title: str
    state: str
    priority: str
    milestone_id: Optional[UUID] = None
    created_at: datetime


class GoalWithRelationsDTO(GoalDTO):
    """Goal with nested milestones and tasks."""

    milestones: List[MilestoneInGoalDTO] = []
    tasks: List[TaskInGoalDTO] = []


class GoalStructureCreateDTO(BaseSchema):
    """Request body for creating a goal with milestones and tasks atomically."""

    goal: GoalCreateDTO
    milestones: List["MilestoneStructureDTO"] = []


class MilestoneStructureDTO(BaseSchema):
    """Milestone with inline tasks for atomic creation."""

    week_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "pending"
    tasks: List["TaskStructureDTO"] = []


class TaskStructureDTO(BaseSchema):
    """Task data for inline creation within a milestone."""

    title: str = Field(..., min_length=1, max_length=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: str = "scheduled"
    priority: str = "standard"
    trigger_type: str = "time"
    is_recurring: bool = False

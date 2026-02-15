from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class GoalStatusEnum(str, Enum):
    """Goal status enum for API."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatusEnum(str, Enum):
    """Task status enum for API."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    RESCHEDULED = "rescheduled"


class NotificationStatusEnum(str, Enum):
    """Notification status enum for API."""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    MISSED = "missed"


# Goal Schemas
class GoalCreate(BaseModel):
    """Schema for creating a goal."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: datetime
    user_id: str = "default_user"  # For future multi-user support


class GoalResponse(BaseModel):
    """Schema for goal response."""
    id: int
    user_id: str
    title: str
    description: Optional[str]
    due_date: datetime
    status: GoalStatusEnum
    created_at: datetime
    updated_at: datetime
    ai_analysis: Optional[str]
    
    model_config = {"from_attributes": True}


# Milestone Schemas
class MilestoneResponse(BaseModel):
    """Schema for milestone response."""
    id: int
    goal_id: int
    title: str
    description: Optional[str]
    week_number: int
    target_date: datetime
    is_completed: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Task Schemas
class TaskResponse(BaseModel):
    """Schema for task response."""
    id: int
    goal_id: int
    milestone_id: Optional[int]
    title: str
    description: Optional[str]
    scheduled_date: datetime
    duration_minutes: int
    status: TaskStatusEnum
    original_date: Optional[datetime]
    reschedule_count: int
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Calendar Event Schemas
class CalendarEventResponse(BaseModel):
    """Schema for calendar event response."""
    id: int
    task_id: Optional[int]
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    is_task_related: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Notification Schemas
class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: int
    task_id: int
    message: str
    scheduled_time: datetime
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    status: NotificationStatusEnum
    created_at: datetime
    
    model_config = {"from_attributes": True}


class NotificationAcknowledge(BaseModel):
    """Schema for acknowledging a notification."""
    notification_id: int
    acknowledged: bool = True


# Goal Breakdown Response
class GoalBreakdownResponse(BaseModel):
    """Complete goal breakdown with milestones and tasks."""
    goal: GoalResponse
    milestones: List[MilestoneResponse]
    tasks: List[TaskResponse]
    total_weeks: int
    total_tasks: int


# Generic Response
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True

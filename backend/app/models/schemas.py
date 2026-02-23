"""
Flux Backend — Pydantic Schemas

Request and response models for the Goal Planner API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────

class ConversationState(str, Enum):
    """Tracks where we are in the goal-planning dialogue."""
    IDLE = "IDLE"
    GATHERING_TIMELINE = "GATHERING_TIMELINE"
    GATHERING_CURRENT_STATE = "GATHERING_CURRENT_STATE"
    GATHERING_TARGET = "GATHERING_TARGET"
    GATHERING_PREFERENCES = "GATHERING_PREFERENCES"
    PLAN_READY = "PLAN_READY"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"


class TaskState(str, Enum):
    SCHEDULED = "scheduled"
    DRIFTED = "drifted"
    COMPLETED = "completed"
    MISSED = "missed"


class TaskPriority(str, Enum):
    STANDARD = "standard"
    IMPORTANT = "important"
    MUST_NOT_MISS = "must-not-miss"


# ── Request Models ──────────────────────────────────────────

class StartGoalRequest(BaseModel):
    """Body for POST /goals/start"""
    user_id: str = Field(..., description="UUID of the user starting the goal")
    message: str = Field(..., description="Initial user message, e.g. 'I want to lose weight for a wedding'")


class RespondRequest(BaseModel):
    """Body for POST /goals/{id}/respond"""
    message: str = Field(..., description="User's response text")


# ── Response Models ─────────────────────────────────────────

class PlanTask(BaseModel):
    title: str
    duration: Optional[str] = None
    recurring: bool = False
    day_of_week: Optional[str] = None


class PlanMilestone(BaseModel):
    week: int
    title: str
    tasks: list[str]


class AgentMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class GoalConversationResponse(BaseModel):
    """Returned by both /start and /respond endpoints."""
    conversation_id: str
    state: ConversationState
    message: str = Field(..., description="AI's response to the user")
    suggested_action: Optional[str] = None
    plan: Optional[list[PlanMilestone]] = None
    goal_id: Optional[str] = None


# ── DB Record Models ───────────────────────────────────────

class GoalRecord(BaseModel):
    id: str
    user_id: str
    title: str
    category: Optional[str] = None
    timeline: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None


class MilestoneRecord(BaseModel):
    id: str
    goal_id: str
    week_number: int
    title: str
    status: str = "pending"


class TaskRecord(BaseModel):
    id: str
    user_id: str
    goal_id: str
    milestone_id: Optional[str] = None
    title: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: TaskState = TaskState.SCHEDULED
    priority: TaskPriority = TaskPriority.STANDARD
    is_recurring: bool = False


# ── Scheduler Models ───────────────────────────────────────

class SchedulerSuggestRequest(BaseModel):
    """Body for POST /scheduler/suggest"""
    event_id: str = Field(..., description="UUID of the drifted task")


class RescheduleSuggestion(BaseModel):
    """A single reschedule option."""
    new_start: datetime
    new_end: datetime
    label: str = Field(..., description="Human-readable label, e.g. '5:00 PM Today'")
    rationale: str = Field(..., description="Why this slot was chosen")


class SchedulerSuggestResponse(BaseModel):
    """Returned by POST /scheduler/suggest"""
    event_id: str
    task_title: str
    suggestions: list[RescheduleSuggestion]
    skip_option: bool = True
    ai_message: str = Field(..., description="Conversational message, e.g. 'Gym drifted. I can do:'")


class SchedulerApplyRequest(BaseModel):
    """Body for POST /scheduler/apply"""
    event_id: str = Field(..., description="UUID of the task to reschedule")
    action: str = Field(..., description="'reschedule' or 'skip'")
    new_start: Optional[datetime] = None
    new_end: Optional[datetime] = None


class SchedulerApplyResponse(BaseModel):
    """Returned by POST /scheduler/apply"""
    event_id: str
    action: str
    new_state: TaskState
    new_start: Optional[datetime] = None
    new_end: Optional[datetime] = None
    message: str

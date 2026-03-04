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


class SourceReference(BaseModel):
    """A single RAG source citation returned alongside a generated plan."""
    title: str
    url: str


class GoalConversationResponse(BaseModel):
    """Returned by both /start and /respond endpoints."""
    conversation_id: str
    state: ConversationState
    message: str = Field(..., description="AI's response to the user")
    suggested_action: Optional[str] = None
    plan: Optional[list[PlanMilestone]] = None
    goal_id: Optional[str] = None
    sources: Optional[list[SourceReference]] = None


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


# ── Orchestrator Models ───────────────────────────────────

class OrchestratorIntent(str, Enum):
    START_GOAL = "START_GOAL"
    CONTINUE_GOAL = "CONTINUE_GOAL"
    LIST_TASKS = "LIST_TASKS"
    SUGGEST_RESCHEDULE = "SUGGEST_RESCHEDULE"
    APPLY_RESCHEDULE = "APPLY_RESCHEDULE"
    VOICE_CREATE_SESSION = "VOICE_CREATE_SESSION"
    VOICE_SAVE_MESSAGE = "VOICE_SAVE_MESSAGE"
    VOICE_GET_MESSAGES = "VOICE_GET_MESSAGES"
    VOICE_PROCESS_INTENT = "VOICE_PROCESS_INTENT"
    VOICE_CLOSE_SESSION = "VOICE_CLOSE_SESSION"
    UNKNOWN = "UNKNOWN"


class OrchestratorMessageRequest(BaseModel):
    """Body for POST /orchestrator/message"""

    user_id: Optional[str] = Field(
        default=None,
        description="UUID of the user. Defaults to demo user when omitted.",
    )
    message: str = Field(default="", description="User chat message")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Goal conversation ID for follow-up messages",
    )
    event_id: Optional[str] = Field(
        default=None,
        description="Task/event ID for scheduler actions",
    )
    action: Optional[str] = Field(
        default=None,
        description="Scheduler action override: 'reschedule' or 'skip'",
    )
    voice_action: Optional[str] = Field(
        default=None,
        description=(
            "Voice operation override: create_session | save_message | "
            "get_messages | process_intent | close_session"
        ),
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Voice session/conversation id for voice operations",
    )
    role: Optional[str] = Field(
        default=None,
        description="Role for voice transcript save: user | assistant | system | function",
    )
    function_call_id: Optional[str] = Field(
        default=None,
        description="Deepgram function call id for process_intent",
    )
    function_name: Optional[str] = Field(
        default=None,
        description="Deepgram function name for process_intent",
    )
    input: Optional[dict] = Field(
        default=None,
        description="Function input payload for process_intent",
    )
    new_start: Optional[datetime] = None
    new_end: Optional[datetime] = None


class OrchestratorMessageResponse(BaseModel):
    """Unified response for orchestration requests."""

    intent: OrchestratorIntent
    route: str = Field(..., description="Route selected by orchestrator")
    message: str = Field(..., description="Top-level orchestration message")
    conversation_id: Optional[str] = None
    goal_state: Optional[ConversationState] = None
    goal_id: Optional[str] = None
    suggested_action: Optional[str] = None
    proposed_plan: Optional[list[PlanMilestone]] = None
    requires_user_action: bool = False
    scheduler_payload: Optional[dict] = None
    voice_payload: Optional[dict] = None


# ── Analytics Response Models (BE-3 · SCRUM-59) ──────────

class HeatmapDay(BaseModel):
    """A single day in the activity heatmap."""
    day: str = Field(..., description="ISO date string, e.g. '2026-03-01'")
    done_count: int = Field(..., description="Number of tasks completed on this day")


class AnalyticsOverviewResponse(BaseModel):
    """GET /analytics/overview"""
    streak_days: int = Field(0, description="Consecutive days with ≥1 done task")
    today_done: int = Field(0, description="Tasks completed today")
    today_total: int = Field(0, description="Total tasks scheduled today")
    today_completion_pct: Optional[float] = Field(
        None, description="Today's completion ratio (0.0–1.0), None if no tasks"
    )
    heatmap: Optional[list[HeatmapDay]] = Field(
        None, description="Daily done counts for the last 365 days"
    )


class AnalyticsWeeklyItem(BaseModel):
    """A single row in GET /analytics/weekly."""
    week_start: str = Field(..., description="ISO date of the Monday starting the week")
    done: int
    total: int
    completion_pct: float = Field(..., description="Completion ratio 0.0–1.0")


class AnalyticsGoalItem(BaseModel):
    """A single goal in GET /analytics/goals."""
    goal_id: str
    title: str
    tasks_done: int
    tasks_total: int
    completion_pct: float = Field(..., description="Completion ratio 0.0–1.0")


class AnalyticsMissedByCategoryItem(BaseModel):
    """A single category in GET /analytics/missed-by-cat."""
    category: str
    missed_count: int

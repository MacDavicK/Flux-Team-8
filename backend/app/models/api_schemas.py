"""
19. API Request/Response Schemas (app/models/api_schemas.py) — §11
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────
# 19.1 — Chat
# ─────────────────────────────────────────────────────────────────


class GoalClarifierAnswer(BaseModel):
    question_id: str  # matches ClarifierQuestion.id
    question: str  # original question text (for context in conversation history)
    answer: str  # user's answer (selected option or custom input)


class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    intent: Optional[str] = None  # Pre-set intent — skips orchestrator LLM call
    task_id: Optional[str] = None  # Required when intent == "RESCHEDULE_TASK"
    reschedule_scope: Optional[str] = (
        None  # "one" | "series" — set after scope selection
    )
    answers: Optional[list[GoalClarifierAnswer]] = (
        None  # Structured answers for GOAL_CLARIFY
    )


class OnboardingStartRequest(BaseModel):
    timezone: Optional[str] = None  # IANA timezone string from the browser


class OnboardingOptionSchema(BaseModel):
    label: str
    value: Optional[str] = None  # None = "Specify" — frontend opens a text input
    zod_validator: Optional[str] = (
        None  # Zod schema string for validating the Specify input
    )
    input_type: Optional[str] = None  # "otp" renders the OTP verification widget


class ClarifierQuestionSchema(BaseModel):
    id: str
    question: str
    options: list[str] = []
    allows_custom: bool = True
    multi_select: bool = False
    zod_validator: Optional[str] = None
    required: bool = True


class RagSource(BaseModel):
    title: str
    url: Optional[str] = None


class ChatMessageResponse(BaseModel):
    conversation_id: str
    message: str
    agent_node: Optional[str] = None
    proposed_plan: Optional[dict] = None
    requires_user_action: bool = False
    options: Optional[list[OnboardingOptionSchema]] = None
    questions: Optional[list[ClarifierQuestionSchema]] = None
    spoken_summary: Optional[str] = None
    rag_used: bool = False
    rag_sources: list[RagSource] = []
    # Congestion-aware start date — populated when agent_node == "ask_start_date"
    suggested_date: Optional[str] = None  # YYYY-MM-DD; lightest day in next 14
    congested_dates: list[str] = []  # YYYY-MM-DD list; fully-booked days


# ─────────────────────────────────────────────────────────────────
# 19.3 — Chat history
# ─────────────────────────────────────────────────────────────────


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    agent_node: Optional[str] = None
    created_at: datetime
    metadata: Optional[dict] = None


class ChatHistoryResponse(BaseModel):
    conversation_id: Optional[str] = None  # None when user has no conversations yet
    messages: list[MessageSchema]


class ConversationSummary(BaseModel):
    id: str
    last_message_at: Optional[datetime] = None
    created_at: datetime
    title: Optional[str] = None  # set once a goal is identified
    preview: Optional[str] = None  # first user message, truncated


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    has_more: bool = False
    next_cursor: Optional[str] = None  # ISO8601 last_message_at for keyset pagination


# ─────────────────────────────────────────────────────────────────
# 19.4 — Goals
# ─────────────────────────────────────────────────────────────────


class GoalResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    class_tags: list[str] = []
    created_at: datetime
    activated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pipeline: Optional[list[dict]] = None


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]


# ─────────────────────────────────────────────────────────────────
# 19.5 — Tasks
# ─────────────────────────────────────────────────────────────────


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    trigger_type: Optional[str] = None
    goal_id: Optional[str] = None
    escalation_policy: str = "standard"
    created_at: datetime


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


# ─────────────────────────────────────────────────────────────────
# 19.6 — Analytics
# ─────────────────────────────────────────────────────────────────


class AnalyticsOverviewResponse(BaseModel):
    streak_days: int
    today_completion_pct: float
    today_done: int
    today_total: int
    heatmap: list[dict]


class WeeklyStatsResponse(BaseModel):
    weeks: list[dict]


class MissedByCatResponse(BaseModel):
    categories: list[dict]


# ─────────────────────────────────────────────────────────────────
# 19.7 — Patterns
# ─────────────────────────────────────────────────────────────────


class PatternResponse(BaseModel):
    id: str
    pattern_type: str
    description: Optional[str] = None
    data: Optional[dict] = None
    confidence: Optional[float] = None
    updated_at: datetime


class PatternPatchRequest(BaseModel):
    user_override: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    confidence: Optional[float] = None


# ─────────────────────────────────────────────────────────────────
# 19.8 — Account
# ─────────────────────────────────────────────────────────────────


class AccountMeResponse(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    timezone: Optional[str] = None
    onboarded: Optional[bool] = None
    phone_verified: Optional[bool] = None
    notification_preferences: Optional[dict] = None
    monthly_token_usage: Optional[dict] = None
    has_tasks: Optional[bool] = None


class AccountPatchRequest(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    notification_preferences: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────
# 19.9 — Phone verify
# ─────────────────────────────────────────────────────────────────


class PhoneVerifySendRequest(BaseModel):
    phone_number: str


class PhoneVerifyConfirmRequest(BaseModel):
    phone_number: str
    code: str


# ─────────────────────────────────────────────────────────────────
# 19.10 — Reschedule
# ─────────────────────────────────────────────────────────────────


class RescheduleRequest(BaseModel):
    message: str


class RescheduleConfirmRequest(BaseModel):
    scheduled_at: str  # ISO 8601 UTC datetime string
    scope: str = "one"  # "one" | "series"


# ─────────────────────────────────────────────────────────────────
# 19.12 — To-do (unscheduled task)
# ─────────────────────────────────────────────────────────────────


class TodoCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None


# ─────────────────────────────────────────────────────────────────
# 19.11 — Goal modify
# ─────────────────────────────────────────────────────────────────


class GoalModifyRequest(BaseModel):
    message: str


# ─────────────────────────────────────────────────────────────────
# 19.13 — Push subscription
# ─────────────────────────────────────────────────────────────────


class PushSubscriptionRequest(BaseModel):
    subscription: dict  # Full PushSubscriptionJSON object from the browser


# ─────────────────────────────────────────────────────────────────
# 19.14 — Escalation policy
# ─────────────────────────────────────────────────────────────────


class EscalationPolicyUpdate(BaseModel):
    escalation_policy: str  # "silent" | "standard" | "aggressive"


# ─────────────────────────────────────────────────────────────────
# 19.15 — Task action (projected occurrence)
# ─────────────────────────────────────────────────────────────────


class TaskActionRequest(BaseModel):
    occurrence_date: Optional[str] = None  # YYYY-MM-DD; only for projected occurrences

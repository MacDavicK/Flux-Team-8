"""
19. API Request/Response Schemas (app/models/api_schemas.py) — §11
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────
# 19.1 — Chat
# ─────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    conversation_id: str
    message: str
    agent_node: Optional[str] = None
    proposed_plan: Optional[dict] = None
    requires_user_action: bool = False


# ─────────────────────────────────────────────────────────────────
# 19.3 — Chat history
# ─────────────────────────────────────────────────────────────────

class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    agent_node: Optional[str] = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[MessageSchema]


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
    timezone: Optional[str] = None
    onboarded: Optional[bool] = None
    phone_verified: Optional[bool] = None
    notification_preferences: Optional[dict] = None
    monthly_token_usage: Optional[dict] = None


class AccountPatchRequest(BaseModel):
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


# ─────────────────────────────────────────────────────────────────
# 19.11 — Goal modify
# ─────────────────────────────────────────────────────────────────

class GoalModifyRequest(BaseModel):
    message: str

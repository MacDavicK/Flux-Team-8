from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Inbound payloads
# ---------------------------------------------------------------------------

class TaskMissSignal(BaseModel):
    """Payload sent when a task is marked as missed."""

    task_id: UUID = Field(..., description="UUID of the missed task")
    user_id: UUID = Field(..., description="UUID of the task owner")
    scheduled_at: datetime = Field(
        ..., description="Original scheduled datetime of the missed task"
    )
    category: Optional[str] = Field(
        None, description="Task category (e.g. Fitness, Learning)"
    )
    consecutive_miss_count: int = Field(
        default=1,
        ge=1,
        description="Number of back-to-back misses detected for this slot",
    )


class ConsultationRequest(BaseModel):
    """Request from Goal Planner or Scheduler to retrieve pattern hints."""

    user_id: UUID = Field(..., description="UUID of the user to analyse")
    lookback_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="How many days of history to include (default uses service config)",
    )


# ---------------------------------------------------------------------------
# LLM-structured output / response models
# ---------------------------------------------------------------------------

class AvoidSlot(BaseModel):
    """A time-slot the user consistently avoids."""

    day: str = Field(..., description="Day of the week (e.g. Monday)")
    time_range: str = Field(..., description="Time range string (e.g. 07:00-09:00)")
    reason: str = Field(..., description="Human-readable reason for the avoidance flag")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )


class CategoryPerformance(BaseModel):
    """Completion rate for a task category."""

    category: str = Field(..., description="Task category name")
    completion_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of tasks completed (0-1)"
    )


class PatternSummary(BaseModel):
    """Structured behavioural pattern summary returned by the LLM."""

    best_times: List[str] = Field(
        default_factory=list,
        description="Time ranges where the user has highest completion rate",
    )
    avoid_slots: List[AvoidSlot] = Field(
        default_factory=list, description="Time slots flagged as avoidance patterns"
    )
    category_performance: List[CategoryPerformance] = Field(
        default_factory=list, description="Per-category completion rates"
    )
    general_notes: str = Field(
        default="", description="Free-text high-level summary of behavioural patterns"
    )
    low_confidence: bool = Field(
        default=False,
        description="True when fewer than 2 weeks of data are available",
    )


# ---------------------------------------------------------------------------
# API responses
# ---------------------------------------------------------------------------

class ConsultationResponse(BaseModel):
    """Full consultation response returned to callers."""

    user_id: UUID
    pattern_summary: PatternSummary
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_points_analysed: int = Field(
        default=0, description="Number of task records used to build the summary"
    )


class MissSignalResponse(BaseModel):
    """Acknowledgement returned after processing a task-miss signal."""

    user_id: UUID
    task_id: UUID
    avoidance_flagged: bool = Field(
        ...,
        description="True when the miss triggered an avoidance-pattern record",
    )
    pattern_id: Optional[UUID] = Field(
        None, description="ID of the created/updated Pattern record (if any)"
    )
    message: str


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    service: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

from typing import Literal, Optional

from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────
# 6.1 — Orchestrator
# ─────────────────────────────────────────────────────────────────

class OrchestratorOutput(BaseModel):
    intent: Literal["GOAL", "NEW_TASK", "RESCHEDULE_TASK", "MODIFY_GOAL", "CLARIFY", "ONBOARDING"]
    payload: dict
    clarification_question: Optional[str] = None
    task_id: Optional[str] = None       # Present when intent == RESCHEDULE_TASK
    goal_id: Optional[str] = None       # Present when intent == MODIFY_GOAL


# ─────────────────────────────────────────────────────────────────
# 6.3 — ProposedTask (used inside GoalPlannerOutput)
# ─────────────────────────────────────────────────────────────────

class ProposedTask(BaseModel):
    title: str
    description: str
    scheduled_days: list[str]           # e.g. ["Monday", "Wednesday", "Friday"]
    suggested_time: str                 # "07:00" — in user local time
    duration_minutes: int
    recurrence_rule: str                # iCal RRULE string
    week_range: list[int]               # e.g. [1, 6]


# ─────────────────────────────────────────────────────────────────
# 6.4 — MicroGoal (used inside GoalPlannerOutput)
# ─────────────────────────────────────────────────────────────────

class MicroGoal(BaseModel):
    title: str
    description: str
    pipeline_order: int
    target_weeks: int = 6


# ─────────────────────────────────────────────────────────────────
# 6.5 — ConflictDetected (used inside GoalPlannerOutput)
# ─────────────────────────────────────────────────────────────────

class ConflictDetected(BaseModel):
    existing_task_title: str
    scheduled_at: str
    message: str                        # Human-readable description of the conflict


# ─────────────────────────────────────────────────────────────────
# 6.2 — GoalPlannerOutput
# ─────────────────────────────────────────────────────────────────

class GoalPlannerOutput(BaseModel):
    goal_feasible_in_6_weeks: bool
    micro_goal_roadmap: Optional[list[MicroGoal]] = None
    proposed_tasks: list[ProposedTask]
    conflicts_detected: list[ConflictDetected] = []
    plan_summary: str                   # Human-readable plan to present to the user
    approval_status: str                # "pending" | "approved" | "negotiating" | "abandoned"


# ─────────────────────────────────────────────────────────────────
# 6.6 — ClassifierOutput
# ─────────────────────────────────────────────────────────────────

class ClassifierOutput(BaseModel):
    tags: list[str]                     # 1–3 tags from the fixed 14-tag taxonomy


# ─────────────────────────────────────────────────────────────────
# 6.8 — SlotResult (used inside SchedulerOutput)
# ─────────────────────────────────────────────────────────────────

class SlotResult(BaseModel):
    task_title: str
    scheduled_at: str                   # ISO8601 UTC
    duration_minutes: int
    conflict: bool = False


# ─────────────────────────────────────────────────────────────────
# 6.7 — SchedulerOutput
# ─────────────────────────────────────────────────────────────────

class SchedulerOutput(BaseModel):
    slots: list[SlotResult]
    conflicts: list[dict]
    first_available_start: Optional[str] = None  # ISO8601 date if no slots available now


# ─────────────────────────────────────────────────────────────────
# 6.10 — AvoidSlot (used inside PatternObserverOutput)
# ─────────────────────────────────────────────────────────────────

class AvoidSlot(BaseModel):
    day: str
    time_range: str
    reason: str
    confidence: float


# ─────────────────────────────────────────────────────────────────
# 6.11 — CategoryPerformance (used inside PatternObserverOutput)
# ─────────────────────────────────────────────────────────────────

class CategoryPerformance(BaseModel):
    category: str
    completion_rate: float


# ─────────────────────────────────────────────────────────────────
# 6.9 — PatternObserverOutput
# ─────────────────────────────────────────────────────────────────

class PatternObserverOutput(BaseModel):
    best_times: list[str]               # e.g. ["07:00–09:00", "18:00–19:30"]
    avoid_slots: list[AvoidSlot]
    category_performance: list[CategoryPerformance]
    general_notes: str

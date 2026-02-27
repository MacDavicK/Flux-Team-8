"""Pydantic-compatible enum classes for API contracts."""

import enum


class TaskState(str, enum.Enum):
    SCHEDULED = "scheduled"
    DRIFTED = "drifted"
    COMPLETED = "completed"
    MISSED = "missed"


class TaskPriority(str, enum.Enum):
    STANDARD = "standard"
    IMPORTANT = "important"
    MUST_NOT_MISS = "must-not-miss"


class TriggerType(str, enum.Enum):
    TIME = "time"
    ON_LEAVING_HOME = "on_leaving_home"

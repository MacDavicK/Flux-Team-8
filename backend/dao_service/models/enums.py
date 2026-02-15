"""Python enum classes matching PostgreSQL enum types."""

import enum


class TaskStateEnum(str, enum.Enum):
    SCHEDULED = "scheduled"
    DRIFTED = "drifted"
    COMPLETED = "completed"
    MISSED = "missed"


class TaskPriorityEnum(str, enum.Enum):
    STANDARD = "standard"
    IMPORTANT = "important"
    MUST_NOT_MISS = "must-not-miss"


class TriggerTypeEnum(str, enum.Enum):
    TIME = "time"
    ON_LEAVING_HOME = "on_leaving_home"

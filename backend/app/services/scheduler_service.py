"""
Flux Backend — Scheduler Service

Database operations for task scheduling: reading tasks, user profiles,
finding free slots, and applying reschedule decisions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.database import get_supabase_client

logger = logging.getLogger(__name__)


def _db():
    return get_supabase_client()


def get_task_by_id(task_id: str) -> Optional[dict]:
    """Fetch a single task by ID. Returns None if not found (use .maybe_single() to avoid exception)."""
    result = (
        _db().table("tasks")
        .select("*")
        .eq("id", task_id)
        .maybe_single()
        .execute()
    )
    return result.data if result.data is not None else None


def get_user_profile(user_id: str) -> Optional[dict]:
    """Fetch user preferences (sleep window, work hours, etc.). Returns None if not found."""
    result = (
        _db().table("users")
        .select("id, name, preferences")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data if result.data is not None else None


def get_tasks_in_range(
    user_id: str,
    range_start: datetime,
    range_end: datetime,
    exclude_task_id: Optional[str] = None,
) -> list[dict]:
    """
    Fetch all non-terminal tasks for a user within a time range.
    Excludes the drifted task itself from conflict detection.
    """
    query = (
        _db().table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .in_("state", ["scheduled", "drifted"])
        .gte("start_time", range_start.isoformat())
        .lte("start_time", range_end.isoformat())
    )
    if exclude_task_id:
        query = query.neq("id", exclude_task_id)

    result = query.execute()
    return result.data or []


def update_task_reschedule(
    task_id: str,
    new_start: datetime,
    new_end: datetime,
) -> dict:
    """Reschedule a task: update times and set state back to 'scheduled'."""
    result = (
        _db().table("tasks")
        .update({
            "start_time": new_start.isoformat(),
            "end_time": new_end.isoformat(),
            "state": "scheduled",
        })
        .eq("id", task_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def mark_task_missed(task_id: str) -> dict:
    """Mark a task as missed (skip today)."""
    result = (
        _db().table("tasks")
        .update({"state": "missed"})
        .eq("id", task_id)
        .execute()
    )
    return result.data[0] if result.data else {}

"""
Flux Backend — Tasks Router

REST endpoints for task management (read, complete, mark missed).
All endpoints require JWT authentication via Supabase.

Prefix: /api/v1/tasks
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def _db():
    return get_supabase_client()


# ── GET /api/v1/tasks/today ──────────────────────────────────
@router.get("/today")
async def get_today_tasks(user: dict = Depends(get_current_user)):
    """
    Return today's tasks for the authenticated user, ordered by scheduled_at.
    """
    user_id = user["sub"]
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    day_end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    result = (
        _db()
        .table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .gte("scheduled_at", day_start)
        .lte("scheduled_at", day_end)
        .order("scheduled_at")
        .execute()
    )

    return {"tasks": result.data or []}


# ── GET /api/v1/tasks/{task_id} ──────────────────────────────
@router.get("/{task_id}")
async def get_task_by_id(task_id: str, user: dict = Depends(get_current_user)):
    """
    Return a single task by ID, scoped to the authenticated user.
    """
    user_id = user["sub"]
    result = (
        _db()
        .table("tasks")
        .select("*")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if result.data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return result.data


# ── PATCH /api/v1/tasks/{task_id}/complete ────────────────────
@router.patch("/{task_id}/complete")
async def mark_task_complete(task_id: str, user: dict = Depends(get_current_user)):
    """
    Mark a task as done: sets status='done' and completed_at=now().
    """
    user_id = user["sub"]

    # Verify the task exists and belongs to the user
    existing = (
        _db()
        .table("tasks")
        .select("id")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if existing.data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    result = (
        _db()
        .table("tasks")
        .update(
            {
                "status": "done",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )

    return result.data[0] if result.data else {"id": task_id, "status": "done"}


# ── PATCH /api/v1/tasks/{task_id}/missed ─────────────────────
@router.patch("/{task_id}/missed")
async def mark_task_missed(task_id: str, user: dict = Depends(get_current_user)):
    """
    Mark a task as missed: sets status='missed'.
    """
    user_id = user["sub"]

    # Verify the task exists and belongs to the user
    existing = (
        _db()
        .table("tasks")
        .select("id")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if existing.data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    result = (
        _db()
        .table("tasks")
        .update({"status": "missed"})
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )

    return result.data[0] if result.data else {"id": task_id, "status": "missed"}

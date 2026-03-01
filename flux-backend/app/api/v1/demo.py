"""Demo API endpoints — §17.8"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.middleware.auth import get_current_user
from app.services.push_service import dispatch_push
from app.services.supabase import db

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/trigger-location")
async def trigger_location(request: Request, user=Depends(get_current_user)) -> dict:
    """17.8.1 — Fire push notifications for all pending location-triggered tasks."""
    user_id = str(user.id)

    tasks = await db.fetch(
        "SELECT id, user_id, title, scheduled_at FROM tasks WHERE user_id = $1 AND status = 'pending' AND trigger_type = 'location'",
        user_id,
    )
    user_row = await db.fetchrow("SELECT push_subscription FROM users WHERE id = $1", user_id)
    push_subscription = user_row["push_subscription"] if user_row else None

    triggered_count = 0
    for task in tasks:
        if push_subscription:
            await dispatch_push(dict(task), push_subscription)
            triggered_count += 1

    return {"triggered": triggered_count}

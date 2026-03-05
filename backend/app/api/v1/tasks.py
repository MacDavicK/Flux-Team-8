"""
Tasks API endpoints — §17.3

GET   /api/v1/tasks/today              — Today's pending tasks in user timezone.
GET   /api/v1/tasks/{task_id}          — Fetch single task.
PATCH /api/v1/tasks/{task_id}/complete — Mark task done; check goal completion + pipeline.
PATCH /api/v1/tasks/{task_id}/missed   — Mark task missed; fire pattern observer async.
POST  /api/v1/tasks/{task_id}/reschedule — Reschedule via LangGraph.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.agents.graph import compiled_graph
from app.middleware.auth import get_current_user
from app.models.api_schemas import ChatMessageResponse, RescheduleRequest
from app.services.supabase import db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/today")
async def get_today_tasks(
    current_user=Depends(get_current_user),
) -> list[dict]:
    """17.3.1 — Return pending tasks scheduled for today in the user's local timezone."""
    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)

    user_row = await db.fetchrow(
        "SELECT timezone FROM users WHERE id = $1",
        user_uuid,
    )
    tz_name: str = "UTC"
    if user_row and user_row["timezone"]:
        tz_name = user_row["timezone"]

    try:
        import zoneinfo
        user_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        import zoneinfo
        user_tz = zoneinfo.ZoneInfo("UTC")

    now_user = datetime.now(user_tz)
    start_of_today = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = start_of_today + timedelta(days=1)

    start_utc = start_of_today.astimezone(timezone.utc)
    end_utc = end_of_today.astimezone(timezone.utc)

    rows = await db.fetch(
        """
        SELECT id, user_id, goal_id, title, description, status,
               scheduled_at, duration_minutes, trigger_type, location_trigger,
               recurrence_rule, shared_with_goal_ids, completed_at, created_at
        FROM tasks
        WHERE user_id = $1
          AND status = 'pending'
          AND scheduled_at >= $2
          AND scheduled_at < $3
        ORDER BY scheduled_at ASC
        """,
        user_uuid,
        start_utc,
        end_utc,
    )

    return [_serialize_task(row) for row in rows]


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.3.2 — Fetch a single task by ID; verify ownership."""
    task = await _fetch_task_or_404(task_id, str(current_user["sub"]))
    return _serialize_task(task)


@router.patch("/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """
    17.3.3 — Mark a task as done. If it is the last pending task on its goal,
    mark the goal completed and activate the next pipeline goal if present.
    """
    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)
    task = await _fetch_task_or_404(task_id, user_id)
    task_uuid = uuid.UUID(task_id)
    goal_uuid = task["goal_id"]

    await db.execute(
        "UPDATE tasks SET status = 'done', completed_at = NOW() WHERE id = $1 AND user_id = $2",
        task_uuid,
        user_uuid,
    )

    if goal_uuid is not None:
        remaining = await db.fetchval(
            """
            SELECT COUNT(*) FROM tasks
            WHERE goal_id = $1 AND user_id = $2 AND status = 'pending' AND id != $3
            """,
            goal_uuid,
            user_uuid,
            task_uuid,
        )

        if (remaining or 0) == 0:
            await db.execute(
                """
                UPDATE goals
                SET status = 'completed', completed_at = NOW()
                WHERE id = $1 AND user_id = $2 AND status != 'completed'
                """,
                goal_uuid,
                user_uuid,
            )
            completed_goal = await db.fetchrow(
                "SELECT parent_goal_id, pipeline_order FROM goals WHERE id = $1",
                goal_uuid,
            )
            if completed_goal and completed_goal["parent_goal_id"] is not None:
                next_order = (completed_goal["pipeline_order"] or 0) + 1
                await db.execute(
                    """
                    UPDATE goals
                    SET status = 'active', activated_at = NOW()
                    WHERE parent_goal_id = $1 AND user_id = $2
                      AND pipeline_order = $3 AND status = 'pipeline'
                    """,
                    completed_goal["parent_goal_id"],
                    user_uuid,
                    next_order,
                )

    return {"task_id": task_id, "status": "done"}


@router.patch("/{task_id}/missed")
async def missed_task(
    task_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.3.4 — Mark a task as missed and trigger the pattern observer asynchronously."""
    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)
    await _fetch_task_or_404(task_id, user_id)
    task_uuid = uuid.UUID(task_id)

    await db.execute(
        "UPDATE tasks SET status = 'missed' WHERE id = $1 AND user_id = $2",
        task_uuid,
        user_uuid,
    )

    asyncio.create_task(_run_pattern_observer(user_id, task_id))

    return {"task_id": task_id, "status": "missed"}


@router.post("/{task_id}/reschedule", response_model=ChatMessageResponse)
async def reschedule_task(
    task_id: str,
    body: RescheduleRequest,
    current_user=Depends(get_current_user),
) -> ChatMessageResponse:
    """17.3.5 — Run the LangGraph agent with a RESCHEDULE_TASK intent."""
    user_id = str(current_user["sub"])
    task = await _fetch_task_or_404(task_id, user_id)

    correlation_id = str(uuid.uuid4())
    state: dict = {
        "user_id": user_id,
        "conversation_history": [{"role": "user", "content": body.message}],
        "intent": "RESCHEDULE_TASK",
        "user_profile": {},
        "goal_draft": None,
        "proposed_tasks": [_serialize_task(task)],
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": correlation_id,
    }

    thread_id = f"reschedule-{task_id}-{correlation_id}"
    result: dict = await compiled_graph.ainvoke(
        state,
        config={"configurable": {"thread_id": thread_id}},
    )

    reply: str = ""
    for msg in reversed(result.get("conversation_history", [])):
        if msg.get("role") == "assistant":
            reply = msg.get("content", "")
            break

    return ChatMessageResponse(
        conversation_id=task_id,
        message=reply,
        agent_node=result.get("intent"),
        proposed_plan=result.get("scheduler_output"),
        requires_user_action=result.get("approval_status") == "pending",
    )


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

async def _fetch_task_or_404(task_id: str, user_id: str):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    task = await db.fetchrow(
        """
        SELECT id, user_id, goal_id, title, description, status,
               scheduled_at, duration_minutes, trigger_type, location_trigger,
               recurrence_rule, shared_with_goal_ids, completed_at, created_at
        FROM tasks WHERE id = $1
        """,
        task_uuid,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if str(task["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return task


def _serialize_task(row) -> dict:
    d = dict(row)
    for k in ("id", "user_id", "goal_id"):
        if d.get(k) is not None:
            d[k] = str(d[k])
    if d.get("shared_with_goal_ids"):
        d["shared_with_goal_ids"] = [str(x) for x in d["shared_with_goal_ids"]]
    for k in ("scheduled_at", "completed_at", "created_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


async def _run_pattern_observer(user_id: str, task_id: str) -> None:
    """Fire-and-forget: run pattern observer for a missed task."""
    try:
        state: dict = {
            "user_id": user_id,
            "conversation_history": [],
            "intent": None,
            "user_profile": {},
            "goal_draft": None,
            "proposed_tasks": None,
            "classifier_output": None,
            "scheduler_output": None,
            "pattern_output": None,
            "approval_status": None,
            "error": None,
            "token_usage": {},
            "correlation_id": str(uuid.uuid4()),
        }
        thread_id = f"pattern-{task_id}-{str(uuid.uuid4())}"
        await compiled_graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        pass
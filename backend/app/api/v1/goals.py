"""
Goals API endpoints — §17.2

GET    /api/v1/goals/                  — List goals (optionally filtered by status).
GET    /api/v1/goals/{goal_id}         — Fetch a single goal.
PATCH  /api/v1/goals/{goal_id}/abandon — Abandon goal and cancel its pending tasks.
PATCH  /api/v1/goals/{goal_id}/modify  — Modify goal via LangGraph agent.
GET    /api/v1/goals/{goal_id}/tasks   — List tasks belonging to a goal.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.graph import compiled_graph
from app.middleware.auth import get_current_user
from app.models.api_schemas import ChatMessageResponse, GoalModifyRequest
from app.services.supabase import db

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/")
async def list_goals(
    status: Optional[str] = Query(None, description="Filter by goal status"),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """17.2.1 — List goals; include pipeline sub-goals as nested array."""
    user_id = uuid.UUID(str(current_user["sub"]))

    if status is not None:
        rows = await db.fetch(
            """
            SELECT id, user_id, title, description, class_tags, status,
                   parent_goal_id, pipeline_order, created_at, activated_at,
                   completed_at, target_weeks, plan_json
            FROM goals
            WHERE user_id = $1 AND status = $2
            ORDER BY created_at DESC
            """,
            user_id,
            status,
        )
    else:
        rows = await db.fetch(
            """
            SELECT id, user_id, title, description, class_tags, status,
                   parent_goal_id, pipeline_order, created_at, activated_at,
                   completed_at, target_weeks, plan_json
            FROM goals
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )

    goals = [dict(row) for row in rows]

    pipeline_parent_ids = {
        g["parent_goal_id"] for g in goals if g.get("parent_goal_id") is not None
    }

    pipeline_children: dict = {}
    if pipeline_parent_ids:
        child_rows = await db.fetch(
            """
            SELECT id, user_id, title, description, class_tags, status,
                   parent_goal_id, pipeline_order, created_at, activated_at,
                   completed_at, target_weeks, plan_json
            FROM goals
            WHERE parent_goal_id = ANY($1::uuid[]) AND user_id = $2
            ORDER BY pipeline_order ASC NULLS LAST
            """,
            list(pipeline_parent_ids),
            user_id,
        )
        for child in child_rows:
            pid = child["parent_goal_id"]
            pipeline_children.setdefault(pid, []).append(dict(child))

    result: list[dict] = []
    for g in goals:
        g_dict = _serialize_goal(g)
        children = pipeline_children.get(g["id"])
        if children:
            g_dict["pipeline"] = [_serialize_goal(c) for c in children]
        result.append(g_dict)

    return result


@router.get("/progress")
async def get_goals_progress(
    current_user=Depends(get_current_user),
) -> list[dict]:
    """Return per-goal progress metrics for all active goals."""
    user_id = uuid.UUID(str(current_user["sub"]))

    rows = await db.fetch(
        """
        SELECT
            g.id,
            g.title,
            g.status,
            g.target_weeks,
            g.activated_at,
            COUNT(*) FILTER (WHERE t.status = 'done')       AS tasks_done,
            COUNT(*) FILTER (WHERE t.status = 'missed')     AS tasks_missed,
            COUNT(*) FILTER (WHERE t.status = 'rescheduled') AS tasks_rescheduled,
            COUNT(*)                                          AS tasks_total,
            EXTRACT(DAY FROM NOW() - g.activated_at)::int    AS days_elapsed,
            (g.target_weeks * 7)                             AS days_total
        FROM goals g
        LEFT JOIN tasks t ON t.goal_id = g.id AND t.user_id = g.user_id
        WHERE g.user_id = $1 AND g.status = 'active'
        GROUP BY g.id
        """,
        user_id,
    )

    result = []
    for row in rows:
        tasks_done = row["tasks_done"] or 0
        tasks_total = row["tasks_total"] or 0
        tasks_missed = row["tasks_missed"] or 0
        tasks_rescheduled = row["tasks_rescheduled"] or 0
        days_elapsed = max(row["days_elapsed"] or 0, 1)
        days_total = row["days_total"] or (row["target_weeks"] * 7) if row["target_weeks"] else 42

        completion_pct = round((tasks_done / tasks_total * 100), 1) if tasks_total else 0.0
        pace = days_elapsed / days_total if days_total else 1
        velocity = round((tasks_done / tasks_total) / pace, 2) if tasks_total and pace else 0.0
        on_track = velocity >= 0.9

        if tasks_done and pace:
            days_to_completion = (tasks_total / (tasks_done / days_elapsed)) if tasks_done else None
            if days_to_completion and row["activated_at"]:
                from datetime import timedelta as _td
                projected = (row["activated_at"] + _td(days=days_to_completion)).date().isoformat()
            else:
                projected = None
        else:
            projected = None

        result.append({
            "goal_id": str(row["id"]),
            "title": row["title"],
            "status": row["status"],
            "target_weeks": row["target_weeks"],
            "activated_at": row["activated_at"].isoformat() if row["activated_at"] else None,
            "days_elapsed": days_elapsed,
            "days_total": days_total,
            "tasks_done": tasks_done,
            "tasks_total": tasks_total,
            "tasks_missed": tasks_missed,
            "tasks_rescheduled": tasks_rescheduled,
            "completion_pct": completion_pct,
            "velocity": velocity,
            "projected_completion_date": projected,
            "on_track": on_track,
        })

    return result


@router.get("/{goal_id}")
async def get_goal(
    goal_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.2.2 — Fetch a single goal by ID; verify ownership."""
    goal = await _fetch_goal_or_404(goal_id, str(current_user["sub"]))
    return _serialize_goal(goal)


@router.patch("/{goal_id}/abandon")
async def abandon_goal(
    goal_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.2.3 — Mark goal as abandoned and cancel its exclusive pending tasks."""
    user_id = str(current_user["sub"])
    await _fetch_goal_or_404(goal_id, user_id)

    goal_uuid = uuid.UUID(goal_id)
    user_uuid = uuid.UUID(user_id)

    await db.execute(
        "UPDATE goals SET status = 'abandoned' WHERE id = $1 AND user_id = $2",
        goal_uuid,
        user_uuid,
    )
    await db.execute(
        """
        UPDATE tasks
        SET status = 'cancelled'
        WHERE goal_id = $1
          AND user_id = $2
          AND status = 'pending'
          AND (shared_with_goal_ids IS NULL OR shared_with_goal_ids = '{}')
        """,
        goal_uuid,
        user_uuid,
    )

    return {"goal_id": goal_id, "status": "abandoned"}


@router.patch("/{goal_id}/modify", response_model=ChatMessageResponse)
async def modify_goal(
    goal_id: str,
    body: GoalModifyRequest,
    current_user=Depends(get_current_user),
) -> ChatMessageResponse:
    """17.2.4 — Invoke the LangGraph agent with a MODIFY_GOAL intent."""
    user_id = str(current_user["sub"])
    goal = await _fetch_goal_or_404(goal_id, user_id)

    correlation_id = str(uuid.uuid4())
    state: dict = {
        "user_id": user_id,
        "conversation_history": [{"role": "user", "content": body.message}],
        "intent": "MODIFY_GOAL",
        "user_profile": {},
        "goal_draft": _serialize_goal(goal),
        "proposed_tasks": None,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": correlation_id,
    }

    thread_id = f"modify-{goal_id}-{correlation_id}"
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
        conversation_id=goal_id,
        message=reply,
        agent_node=result.get("intent"),
        proposed_plan=result.get("goal_draft"),
        requires_user_action=result.get("approval_status") == "pending",
    )


@router.get("/{goal_id}/tasks")
async def get_goal_tasks(
    goal_id: str,
    current_user=Depends(get_current_user),
) -> list[dict]:
    """17.2.5 — Return all tasks belonging to a goal."""
    user_id = str(current_user["sub"])
    await _fetch_goal_or_404(goal_id, user_id)

    rows = await db.fetch(
        """
        SELECT id, user_id, goal_id, title, description, status,
               scheduled_at, duration_minutes, trigger_type, location_trigger,
               recurrence_rule, shared_with_goal_ids, completed_at, created_at
        FROM tasks
        WHERE goal_id = $1 AND user_id = $2
        ORDER BY scheduled_at ASC NULLS LAST
        """,
        uuid.UUID(goal_id),
        uuid.UUID(user_id),
    )

    return [_serialize_task(row) for row in rows]


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

async def _fetch_goal_or_404(goal_id: str, user_id: str):
    try:
        goal_uuid = uuid.UUID(goal_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal = await db.fetchrow(
        """
        SELECT id, user_id, title, description, class_tags, status,
               parent_goal_id, pipeline_order, created_at, activated_at,
               completed_at, target_weeks, plan_json
        FROM goals WHERE id = $1
        """,
        goal_uuid,
    )
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    if str(goal["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return goal


def _serialize_goal(row) -> dict:
    d = dict(row)
    for k in ("id", "user_id", "parent_goal_id"):
        if d.get(k) is not None:
            d[k] = str(d[k])
    for k in ("created_at", "activated_at", "completed_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


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
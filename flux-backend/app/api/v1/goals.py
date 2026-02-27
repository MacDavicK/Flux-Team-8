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
    user_id = uuid.UUID(str(current_user.id))

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


@router.get("/{goal_id}")
async def get_goal(
    goal_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.2.2 — Fetch a single goal by ID; verify ownership."""
    goal = await _fetch_goal_or_404(goal_id, str(current_user.id))
    return _serialize_goal(goal)


@router.patch("/{goal_id}/abandon")
async def abandon_goal(
    goal_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """17.2.3 — Mark goal as abandoned and cancel its exclusive pending tasks."""
    user_id = str(current_user.id)
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
    user_id = str(current_user.id)
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
    user_id = str(current_user.id)
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
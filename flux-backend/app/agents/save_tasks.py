"""
11.2 — save_tasks node (§11).

Bulk-inserts confirmed task rows into the database. Handles three entry paths:
  - GOAL flow    : goal_planner approved → proposed_tasks + scheduler_output slots
  - NEW_TASK flow: task_handler → proposed_tasks already have scheduled_at (UTC)
  - MODIFY_GOAL  : goal_modifier → same as GOAL flow with an existing goal_id

For recurring tasks the rrule_expander materialises one row per occurrence.
`shared_with_goal_ids` is preserved on every inserted row.
"""

from __future__ import annotations

import json
from typing import Optional

import pendulum

from app.agents.state import AgentState
from app.services.rrule_expander import expand_rrule_to_tasks
from app.services.supabase import db


# ─────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────


def _goal_title_from_plan(plan: dict) -> str:
    """Derive a short goal title from the plan summary (max 100 chars)."""
    summary = plan.get("plan_summary", "") or ""
    # Use first sentence or first 100 chars, whichever is shorter
    first_sentence = summary.split(".")[0].strip()
    title = first_sentence if first_sentence else summary
    return title[:100] or "New Goal"


async def _ensure_goal(user_id: str, goal_draft: dict) -> Optional[str]:
    """
    Return the goal_id for the current GOAL flow.
    If goal_draft has no goal_id yet (new goal), INSERT the goal row and return
    the generated UUID. Returns None when there is no GOAL context (NEW_TASK flow).
    """
    goal_id = goal_draft.get("goal_id")
    plan = goal_draft.get("plan") or {}

    if goal_id:
        return str(goal_id)

    if not plan:
        # NEW_TASK flow — no goal involved
        return None

    # Create the active goal for a freshly negotiated plan
    new_id = await db.fetchval(
        """
        INSERT INTO goals (user_id, title, description, status, activated_at, plan_json)
        VALUES ($1, $2, $3, 'active', now(), $4::jsonb)
        RETURNING id
        """,
        user_id,
        _goal_title_from_plan(plan),
        plan.get("plan_summary", ""),
        json.dumps(plan),
    )
    return str(new_id) if new_id else None


async def _insert_task(row: dict) -> None:
    """INSERT a single task row; asyncpg handles Python types natively."""
    scheduled_at = row.get("scheduled_at")
    # Parse ISO8601 strings into datetime objects that asyncpg accepts as TIMESTAMPTZ
    if isinstance(scheduled_at, str):
        try:
            scheduled_at = pendulum.parse(scheduled_at)
        except Exception:
            scheduled_at = None

    await db.execute(
        """
        INSERT INTO tasks (
            user_id, goal_id, title, description, status,
            scheduled_at, duration_minutes, trigger_type, location_trigger,
            recurrence_rule, shared_with_goal_ids
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        row.get("user_id"),
        row.get("goal_id"),          # None for standalone tasks
        row.get("title", ""),
        row.get("description", ""),
        row.get("status", "pending"),
        scheduled_at,
        row.get("duration_minutes", 30),
        row.get("trigger_type", "time"),
        row.get("location_trigger"),
        row.get("recurrence_rule"),
        row.get("shared_with_goal_ids") or [],
    )


# ─────────────────────────────────────────────────────────────────
# 11.2 — Main node
# ─────────────────────────────────────────────────────────────────


async def save_tasks_node(state: AgentState) -> dict:
    """
    Bulk-inserts all confirmed proposed_tasks into the database.

    GOAL flow:
      - Creates the goal row if it doesn't exist yet.
      - Merges proposed_tasks with scheduler_output slots (matched by task title)
        to get the actual UTC scheduled_at for each task.
      - Expands recurring tasks via rrule_expander (one DB row per occurrence).

    NEW_TASK flow:
      - proposed_tasks already carry a UTC scheduled_at from task_handler.
      - Recurring tasks are expanded for 52 weeks (standalone tasks have no sprint).

    MODIFY_GOAL flow (task 11.3):
      - Same as GOAL flow; existing goal_id comes through goal_draft.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}
    user_tz: str = profile.get("timezone", "UTC")
    proposed_tasks: list[dict] = list(state.get("proposed_tasks") or [])
    goal_draft: dict = state.get("goal_draft") or {}
    scheduler_output: dict = state.get("scheduler_output") or {}
    history: list[dict] = list(state.get("conversation_history") or [])

    # ── Step 1: Resolve or create goal ───────────────────────────────────
    goal_id = await _ensure_goal(user_id, goal_draft)

    # ── Step 2: Build slot lookup (GOAL / MODIFY_GOAL flows only) ────────
    slots_by_title: dict[str, dict] = {
        slot["task_title"]: slot
        for slot in (scheduler_output.get("slots") or [])
    }

    # ── Step 3: Insert each proposed task ────────────────────────────────
    rows_inserted = 0

    for task in proposed_tasks:
        title: str = task.get("title", "")
        task_goal_id = task.get("goal_id") or goal_id   # standalone → None
        duration_minutes: int = task.get("duration_minutes") or 30
        recurrence_rule: Optional[str] = task.get("recurrence_rule")
        trigger_type: str = task.get("trigger_type") or "time"
        location_trigger: Optional[str] = task.get("location_trigger")
        shared_with_goal_ids: list = task.get("shared_with_goal_ids") or []
        week_range: list[int] = task.get("week_range") or []

        # Determine scheduled_at: task dict wins, scheduler slot is fallback
        scheduled_at_utc: Optional[str] = task.get("scheduled_at")
        slot = slots_by_title.get(title)
        if not scheduled_at_utc and slot:
            scheduled_at_utc = slot.get("scheduled_at")
        if not scheduled_at_utc and slot:
            duration_minutes = slot.get("duration_minutes") or duration_minutes

        base_row: dict = {
            "user_id": user_id,
            "goal_id": task_goal_id,
            "title": title,
            "description": task.get("description", ""),
            "status": "pending",
            "duration_minutes": duration_minutes,
            "trigger_type": trigger_type,
            "location_trigger": location_trigger,
            "shared_with_goal_ids": shared_with_goal_ids,
        }

        if recurrence_rule and scheduled_at_utc:
            # Convert UTC start → local wall-clock for rrule dtstart
            try:
                start_utc = pendulum.parse(scheduled_at_utc)
            except Exception:
                start_utc = pendulum.now("UTC")
            start_local = start_utc.in_timezone(user_tz)

            # Expansion horizon: sprint end for goal tasks, 1 year for standalone
            if task_goal_id and week_range:
                expansion_weeks = week_range[-1]
            elif task_goal_id:
                expansion_weeks = 6   # default sprint length
            else:
                expansion_weeks = 52  # standalone recurring task — expand 1 year

            end_local = start_local.add(weeks=expansion_weeks)

            expanded = expand_rrule_to_tasks(
                base_task=base_row,
                rrule_string=recurrence_rule,
                start_dt=start_local,
                end_dt=end_local,
                user_timezone=user_tz,
            )
            for row in expanded:
                await _insert_task(row)
                rows_inserted += 1

        else:
            # One-off task (or no recurrence) — single insert
            await _insert_task({
                **base_row,
                "scheduled_at": scheduled_at_utc,
                "recurrence_rule": recurrence_rule,
            })
            rows_inserted += 1

    # ── Step 4: Build summary reply ───────────────────────────────────────
    if rows_inserted > 0:
        noun = "task" if rows_inserted == 1 else "tasks"
        summary = f"Done! {rows_inserted} {noun} added to your schedule."
    else:
        summary = "No tasks were saved — nothing to schedule."

    updated_goal_draft = {**goal_draft, "goal_id": goal_id} if goal_id else goal_draft

    return {
        "conversation_history": history + [
            {"role": "assistant", "content": summary}
        ],
        "goal_draft": updated_goal_draft,
    }

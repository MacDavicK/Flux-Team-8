"""
Shared recurring-task advance logic.

Called from:
  - notifier/poll.py   (auto-miss path)
  - app/api/v1/tasks.py (complete + missed endpoints)

For any recurring task that transitions out of 'pending' (done or missed),
advance_recurring_task() inserts the next occurrence — subject to the goal's
active timeframe when the task belongs to a goal.
"""

from __future__ import annotations

import logging

import pendulum

from app.services.rrule_expander import next_occurrence_after
from app.services.supabase import db

logger = logging.getLogger(__name__)


async def advance_recurring_task(task_id: str) -> bool:
    """
    If task_id is a recurring task, insert the next pending occurrence.

    Goal timeframe guard: when the task has a goal_id, fetch the goal's
    activated_at + target_weeks to compute the sprint end. If the next
    occurrence falls after the sprint end, do not insert.

    Returns True if a new row was inserted, False otherwise.
    """
    task_row = await db.fetchrow(
        """
        SELECT id, recurrence_rule, scheduled_at, user_id, title, description,
               duration_minutes, trigger_type, location_trigger,
               goal_id, shared_with_goal_ids, escalation_policy
        FROM tasks WHERE id = $1
        """,
        task_id,
    )
    if not task_row or not task_row["recurrence_rule"] or not task_row["scheduled_at"]:
        return False

    user_id = str(task_row["user_id"])

    tz_row = await db.fetchrow("SELECT timezone FROM users WHERE id = $1", user_id)
    user_tz = (tz_row["timezone"] if tz_row else None) or "UTC"

    scheduled_at = task_row["scheduled_at"]
    ref_dt = (
        pendulum.instance(scheduled_at)
        if hasattr(scheduled_at, "isoformat")
        else pendulum.parse(str(scheduled_at))
    )

    next_utc = next_occurrence_after(
        rrule_string=task_row["recurrence_rule"],
        after_dt=ref_dt,
        user_timezone=user_tz,
    )
    if next_utc is None:
        logger.info("No further occurrences for recurring task %s", task_id)
        return False

    # Goal timeframe guard
    goal_id = task_row["goal_id"]
    if goal_id is not None:
        goal_row = await db.fetchrow(
            "SELECT activated_at, target_weeks, status FROM goals WHERE id = $1",
            goal_id,
        )
        if goal_row and goal_row["status"] in ("completed", "abandoned"):
            logger.info(
                "Goal %s is %s — not advancing recurring task %s",
                goal_id,
                goal_row["status"],
                task_id,
            )
            return False
        if goal_row and goal_row["activated_at"] and goal_row["target_weeks"]:
            sprint_end = pendulum.instance(goal_row["activated_at"]).add(
                weeks=goal_row["target_weeks"]
            )
            next_dt = pendulum.parse(next_utc)
            if next_dt > sprint_end:
                logger.info(
                    "Next occurrence %s is past sprint end %s — not advancing recurring task %s",
                    next_utc,
                    sprint_end.isoformat(),
                    task_id,
                )
                return False

    shared_ids = task_row["shared_with_goal_ids"] or []

    await db.execute(
        """
        INSERT INTO tasks (
            user_id, goal_id, title, description, status,
            scheduled_at, duration_minutes, trigger_type, location_trigger,
            recurrence_rule, shared_with_goal_ids, escalation_policy
        ) VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9, $10, $11)
        """,
        user_id,
        goal_id,
        task_row["title"],
        task_row["description"],
        pendulum.parse(next_utc),
        task_row["duration_minutes"],
        task_row["trigger_type"],
        task_row["location_trigger"],
        task_row["recurrence_rule"],
        shared_ids,
        task_row["escalation_policy"],
    )
    logger.info("Advanced recurring task %s → next occurrence at %s", task_id, next_utc)
    return True

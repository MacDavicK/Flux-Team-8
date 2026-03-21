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

from app.services.rrule_expander import advance_past_sleep, next_occurrence_after
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
               goal_id, shared_with_goal_ids, escalation_policy, proposed_time
        FROM tasks WHERE id = $1
        """,
        task_id,
    )
    if not task_row or not task_row["recurrence_rule"] or not task_row["scheduled_at"]:
        return False

    user_id = str(task_row["user_id"])

    tz_row = await db.fetchrow(
        "SELECT timezone, profile FROM users WHERE id = $1", user_id
    )
    user_tz = (tz_row["timezone"] if tz_row else None) or "UTC"
    sleep_window = None
    if tz_row and tz_row["profile"]:
        profile_data = tz_row["profile"] if isinstance(tz_row["profile"], dict) else {}
        sleep_window = profile_data.get("sleep_window")

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

    # If proposed_time is set, override the time component of next_utc with the
    # canonical wall-clock time. This ensures a single-occurrence reschedule
    # (which only changed scheduled_at, not proposed_time) reverts correctly.
    # proposed_time restores the canonical wall-clock time after a
    # single-occurrence reschedule (which changes scheduled_at but not
    # proposed_time). This only makes sense for day-or-longer frequencies
    # where there is a single canonical time-of-day per occurrence.
    # Sub-daily rules (MINUTELY, HOURLY) have no meaningful canonical
    # time-of-day — applying the override there causes the same timestamp
    # to be re-inserted on every advance, creating an infinite miss loop.
    proposed_time = task_row["proposed_time"]
    _SUB_DAILY = ("MINUTELY", "HOURLY")
    rrule_upper = (task_row["recurrence_rule"] or "").upper()
    _proposed_time_applies = proposed_time is not None and not any(
        f"FREQ={f}" in rrule_upper for f in _SUB_DAILY
    )

    if _proposed_time_applies:
        try:
            proposed_hour, proposed_minute = divmod(proposed_time, 60)
            next_local = pendulum.parse(next_utc).in_timezone(user_tz)
            next_local = next_local.set(
                hour=proposed_hour, minute=proposed_minute, second=0, microsecond=0
            )
            next_utc = next_local.in_timezone("UTC").isoformat()
        except Exception as exc:
            logger.warning(
                "Could not apply proposed_time to next occurrence of task %s: %s",
                task_id,
                exc,
            )

    # Sleep-window guard: advance next_utc past sleep if it lands during sleep.
    # Applied after proposed_time so the restored wall-clock time is also checked.
    if sleep_window and next_utc:
        try:
            dt_for_dtstart = pendulum.parse(next_utc)
            next_utc = advance_past_sleep(
                utc_iso=next_utc,
                sleep_window=sleep_window,
                user_timezone=user_tz,
                rrule_string=task_row["recurrence_rule"],
                dtstart=dt_for_dtstart,
            )
        except Exception as exc:
            logger.warning(
                "Sleep-window advance failed for recurring task %s: %s", task_id, exc
            )

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
            recurrence_rule, shared_with_goal_ids, escalation_policy, proposed_time
        ) VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9, $10, $11, $12)
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
        task_row["proposed_time"],
    )
    logger.info("Advanced recurring task %s → next occurrence at %s", task_id, next_utc)
    return True

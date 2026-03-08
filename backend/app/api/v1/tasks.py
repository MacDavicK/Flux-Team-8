"""
Tasks API endpoints — §17.3

GET   /api/v1/tasks                            — Tasks for a given date (defaults to today) in user timezone.
GET   /api/v1/tasks/{task_id}                  — Fetch single task.
PATCH /api/v1/tasks/{task_id}/complete         — Mark task done; check goal completion + pipeline.
PATCH /api/v1/tasks/{task_id}/missed           — Mark task missed; fire pattern observer async.
PATCH /api/v1/tasks/{task_id}/reschedule-confirm — Confirm a reschedule slot.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pendulum
from fastapi import APIRouter, Depends, HTTPException

from app.agents.graph import compiled_graph
from app.middleware.auth import get_current_user
from app.models.api_schemas import EscalationPolicyUpdate, OnboardingOptionSchema, RescheduleConfirmRequest, TodoCreateRequest
from app.services.recurrence import advance_recurring_task
from app.services.supabase import db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def get_tasks(
    current_user=Depends(get_current_user),
    date: str | None = None,
) -> list[dict]:
    """17.3.1 — Return tasks scheduled for a given date (YYYY-MM-DD) in the user's local timezone.
    Defaults to today when no date is provided."""
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

    if date:
        try:
            parsed = datetime.strptime(date, "%Y-%m-%d")
            start_of_today = datetime(parsed.year, parsed.month, parsed.day, tzinfo=user_tz)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format; expected YYYY-MM-DD")
    else:
        now_user = datetime.now(user_tz)
        start_of_today = now_user.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = start_of_today + timedelta(days=1)

    start_utc = start_of_today.astimezone(timezone.utc)
    end_utc = end_of_today.astimezone(timezone.utc)

    scheduled_rows = await db.fetch(
        """
        SELECT t.id, t.user_id, t.goal_id, t.title, t.description, t.status,
               t.scheduled_at, t.duration_minutes, t.trigger_type, t.location_trigger,
               t.recurrence_rule, t.shared_with_goal_ids, t.escalation_policy, t.completed_at, t.created_at,
               g.title AS goal_name
        FROM tasks t
        LEFT JOIN goals g ON g.id = t.goal_id
        WHERE t.user_id = $1
          AND t.status IN ('pending', 'rescheduled', 'missed', 'done')
          AND t.scheduled_at >= $2
          AND t.scheduled_at < $3
        ORDER BY t.scheduled_at ASC
        """,
        user_uuid,
        start_utc,
        end_utc,
    )

    # Unscheduled todos only appear when viewing today (not historical dates)
    todo_rows = []
    if not date:
        todo_rows = await db.fetch(
            """
            SELECT t.id, t.user_id, t.goal_id, t.title, t.description, t.status,
                   t.scheduled_at, t.duration_minutes, t.trigger_type, t.location_trigger,
                   t.recurrence_rule, t.shared_with_goal_ids, t.escalation_policy, t.completed_at, t.created_at,
                   g.title AS goal_name
            FROM tasks t
            LEFT JOIN goals g ON g.id = t.goal_id
            WHERE t.user_id = $1
              AND t.status = 'pending'
              AND t.scheduled_at IS NULL
            ORDER BY t.created_at ASC
            """,
            user_uuid,
        )

    return [_serialize_task(row) for row in scheduled_rows] + [_serialize_task(row) for row in todo_rows]


@router.post("/todo")
async def create_todo(
    body: TodoCreateRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """Create an unscheduled to-do task (no scheduled_at, no LangGraph)."""
    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)

    task_id = await db.fetchval(
        """
        INSERT INTO tasks (user_id, title, description, status, trigger_type)
        VALUES ($1, $2, $3, 'pending', 'time')
        RETURNING id
        """,
        user_uuid,
        body.title,
        body.description or "",
    )

    return {"task_id": str(task_id), "title": body.title, "status": "pending"}


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

    asyncio.create_task(advance_recurring_task(task_id))

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

    asyncio.create_task(advance_recurring_task(task_id))
    asyncio.create_task(_run_pattern_observer(user_id, task_id))

    return {"task_id": task_id, "status": "missed"}


@router.patch("/{task_id}/escalation-policy")
async def update_escalation_policy(
    task_id: str,
    body: EscalationPolicyUpdate,
    current_user=Depends(get_current_user),
) -> dict:
    """17.3.6 — Update the escalation policy for a task (silent | standard | aggressive)."""
    valid = {"silent", "standard", "aggressive"}
    if body.escalation_policy not in valid:
        raise HTTPException(status_code=422, detail=f"escalation_policy must be one of {sorted(valid)}")

    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    updated = await db.fetchval(
        """
        UPDATE tasks SET escalation_policy = $1
        WHERE id = $2 AND user_id = $3
        RETURNING id
        """,
        body.escalation_policy,
        task_uuid,
        user_uuid,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task = await _fetch_task_or_404(task_id, user_id)
    return _serialize_task(task)


@router.patch("/{task_id}/reschedule-confirm")
async def reschedule_confirm(
    task_id: str,
    body: RescheduleConfirmRequest,
    current_user=Depends(get_current_user),
) -> dict:
    """Confirm a reschedule slot.

    Keeps the original task as 'missed' (preserving pattern-observer data) and
    creates a new 'pending' task at the chosen time. Returns the new task's ID.
    """
    user_id = str(current_user["sub"])
    user_uuid = uuid.UUID(user_id)
    task = await _fetch_task_or_404(task_id, user_id)
    task_uuid = uuid.UUID(task_id)

    try:
        scheduled_at_dt = datetime.fromisoformat(body.scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid scheduled_at format; expected ISO 8601")

    if task["goal_id"] is None:
        # Silent task (no goal) — mutate in place; no new row needed.
        # Reset reminder_sent_at so the notifier fires again at the new time.
        await db.execute(
            "UPDATE tasks SET scheduled_at = $1, status = 'pending', reminder_sent_at = NULL WHERE id = $2 AND user_id = $3",
            scheduled_at_dt,
            task_uuid,
            user_uuid,
        )
        return {
            "original_task_id": task_id,
            "new_task_id": task_id,
            "status": "rescheduled",
            "scheduled_at": scheduled_at_dt.isoformat(),
        }

    # Goal-linked task — mark original missed (preserves pattern-observer data)
    # and create a new pending task for the rescheduled slot.
    await db.execute(
        "UPDATE tasks SET status = 'missed' WHERE id = $1 AND user_id = $2",
        task_uuid,
        user_uuid,
    )

    new_task_id = await db.fetchval(
        """
        INSERT INTO tasks (
            user_id, goal_id, title, description, status,
            scheduled_at, duration_minutes, trigger_type,
            recurrence_rule, escalation_policy
        )
        VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9)
        RETURNING id
        """,
        user_uuid,
        task["goal_id"],
        task["title"],
        task["description"],
        scheduled_at_dt,
        task["duration_minutes"],
        task["trigger_type"],
        task["recurrence_rule"],
        task["escalation_policy"],
    )

    return {
        "original_task_id": task_id,
        "new_task_id": str(new_task_id),
        "status": "rescheduled",
        "scheduled_at": scheduled_at_dt.isoformat(),
    }


async def _compute_simple_reschedule_slots(
    task: dict,
    user_id: str,
    user_tz: str,
) -> list[dict]:
    """
    For tasks without a recurrence_rule, compute up to 3 next-hourly slots
    that don't overlap with existing pending/rescheduled tasks today, plus
    a "Tomorrow, same time" slot.

    Returns a list of dicts: [{"scheduled_at": <UTC ISO>, "label": <str>}]
    """
    tz = pendulum.timezone(user_tz)
    now_local = pendulum.now(tz)

    # Determine original time-of-day from task's scheduled_at (fall back to now)
    original_hour: int = now_local.hour
    original_minute: int = now_local.minute
    task_scheduled_at = task.get("scheduled_at")
    if task_scheduled_at:
        try:
            orig_dt = pendulum.parse(task_scheduled_at).in_timezone(tz)  # type: ignore[union-attr]
            original_hour = orig_dt.hour
            original_minute = orig_dt.minute
        except Exception:
            pass

    duration = int(task.get("duration_minutes") or 30)

    # Fetch existing tasks for today to detect clashes
    today_local = now_local.start_of("day")
    tomorrow_local = today_local.add(days=1)
    existing = await db.fetch(
        """
        SELECT scheduled_at, duration_minutes
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND scheduled_at >= $2
          AND scheduled_at < $3
        ORDER BY scheduled_at
        """,
        uuid.UUID(user_id),
        today_local.in_timezone("UTC"),
        tomorrow_local.add(days=1).in_timezone("UTC"),  # include tomorrow
    )

    busy_intervals: list[tuple[pendulum.DateTime, pendulum.DateTime]] = []
    for row in existing:
        if row["scheduled_at"] is None:
            continue
        start = pendulum.instance(row["scheduled_at"]).in_timezone(tz)
        end = start.add(minutes=int(row["duration_minutes"] or 30))
        busy_intervals.append((start, end))

    def _overlaps(candidate: pendulum.DateTime) -> bool:
        cand_end = candidate.add(minutes=duration)
        for b_start, b_end in busy_intervals:
            # 15-minute buffer
            if candidate < b_end.add(minutes=15) and cand_end > b_start.subtract(minutes=15):
                return True
        return False

    slots: list[dict] = []

    # --- Today: next hourly intervals starting from the next whole hour ---
    # Cap at 5 so the "Tomorrow, same time" slot always fits within the 6-slot limit (7 total with "Mark as Missed").
    candidate = now_local.add(hours=1).replace(minute=0, second=0, microsecond=0)
    end_of_today = now_local.end_of("day")
    while candidate <= end_of_today and len(slots) < 5:
        if not _overlaps(candidate):
            slots.append({
                "scheduled_at": candidate.in_timezone("UTC").isoformat(),
                "label": candidate.format("ddd, MMM D [at] h:mm A"),
            })
        candidate = candidate.add(hours=1)

    # --- Tomorrow, same time ---
    tomorrow_same = tomorrow_local.replace(
        hour=original_hour, minute=original_minute, second=0, microsecond=0
    )
    slots.append({
        "scheduled_at": tomorrow_same.in_timezone("UTC").isoformat(),
        "label": f"Tomorrow at {tomorrow_same.format('h:mm A')}",
    })

    return slots


def _build_slot_options(
    slots: list[dict],
    user_tz: str,
    task_id: str,
) -> list[OnboardingOptionSchema]:
    """Convert up to 6 scheduler slots into button options, plus a date-time picker option."""
    options: list[OnboardingOptionSchema] = []
    tz = pendulum.timezone(user_tz)

    for slot in slots[:6]:
        raw_at = slot.get("scheduled_at", "")
        if not raw_at:
            continue
        try:
            dt_utc = pendulum.parse(raw_at)
            dt_local = dt_utc.in_timezone(tz)  # type: ignore[union-attr]
            label = dt_local.format("ddd, MMM D [at] h:mm A")
        except Exception:
            label = raw_at

        options.append(OnboardingOptionSchema(
            label=label,
            value=raw_at,  # ISO UTC — backend uses this to update scheduled_at
        ))

    options.append(OnboardingOptionSchema(
        label="Pick a date & time",
        value=None,
        input_type="datetime",
    ))

    return options


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

async def _fetch_task_or_404(task_id: str, user_id: str) -> dict:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    task = await db.fetchrow(
        """
        SELECT id, user_id, goal_id, title, description, status,
               scheduled_at, duration_minutes, trigger_type, location_trigger,
               recurrence_rule, shared_with_goal_ids, escalation_policy, completed_at, created_at
        FROM tasks WHERE id = $1
        """,
        task_uuid,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if str(task["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return dict(task)  # type: ignore[arg-type]


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
    # goal_name is already a string (or None) from the LEFT JOIN
    if "goal_name" not in d:
        d["goal_name"] = None
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
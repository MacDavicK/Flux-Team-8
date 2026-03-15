import json
from pathlib import Path

import pendulum

from app.agents.state import AgentState
from app.models.agent_outputs import SchedulerOutput
from app.services.llm import validated_llm_call
from app.services.rrule_expander import projected_occurrences_in_window
from app.services.supabase import db

# 9.4.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "scheduler.txt").read_text()

_MODEL = "openrouter/openai/gpt-4o-mini"


def _parse_as_local(raw: str, tz: object) -> pendulum.DateTime:
    """Parse an ISO8601 string as a local-tz datetime, stripping any offset suffix first."""
    naive = raw
    if naive.endswith("Z"):
        naive = naive[:-1]
    plus_idx = naive.find("+", 10)  # search for offset marker after date portion
    if plus_idx != -1:
        naive = naive[:plus_idx]
    return pendulum.parse(naive, tz=tz)  # type: ignore[return-value, arg-type]


async def scheduler_node(state: AgentState) -> dict:
    """
    Finds available time slots for the proposed tasks over the next 6 weeks.
    Returns SchedulerOutput with UTC-converted scheduled_at values.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}
    goal_draft: dict = state.get("goal_draft") or {}
    pattern_output: dict = state.get("pattern_output") or {}

    user_tz = profile.get("timezone", "UTC")

    # ── Compute planning window ────────────────────────────────────────────
    # Use goal_start_date (user's chosen start) as the window lower bound when
    # available. This fixes BUG #2: previously the window always started at
    # now() even when goal_start_date was set to next Monday.
    goal_start_date: str | None = state.get("goal_start_date")
    if goal_start_date:
        # Parse date-only string ("2026-03-23") in user's timezone so midnight
        # local time is the anchor, then convert to UTC.
        window_start = (
            pendulum.parse(goal_start_date, tz=pendulum.timezone(user_tz))
            .start_of("day")
            .in_timezone("UTC")
        )
    else:
        window_start = pendulum.now("UTC")
    window_end = window_start.add(weeks=6)

    # ── 1. Materialized tasks (real DB rows in the window) ─────────────────
    existing_rows = await db.fetch(
        """
        SELECT title, scheduled_at, duration_minutes
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND scheduled_at >= $2
          AND scheduled_at <= $3
        ORDER BY scheduled_at
        """,
        user_id,
        window_start,
        window_end,
    )
    existing_tasks_data: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (title, scheduled_at ISO) dedup key
    for row in existing_rows:
        iso = row["scheduled_at"].isoformat()
        existing_tasks_data.append(
            {
                "title": row["title"],
                "scheduled_at": iso,
                "duration_minutes": row["duration_minutes"],
                "is_projected": False,
            }
        )
        seen.add((row["title"], iso))

    # ── 2. RRULE projections (virtual future occurrences of recurring tasks) ─
    # Fixes BUG #1: fetch ALL pending recurring tasks and expand their RRULE
    # into the planning window. These occurrences don't exist as DB rows yet
    # but are hard time blocks for the scheduler.
    recurring_rows = await db.fetch(
        """
        SELECT title, scheduled_at, duration_minutes, recurrence_rule
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND recurrence_rule IS NOT NULL
        """,
        user_id,
    )
    for rec in recurring_rows:
        anchor = pendulum.instance(rec["scheduled_at"])
        for proj in projected_occurrences_in_window(
            rec["recurrence_rule"], anchor, window_start, window_end, user_tz
        ):
            key = (rec["title"], proj["scheduled_at"])
            if key in seen:
                continue  # already covered by the materialized query (same slot)
            existing_tasks_data.append(
                {
                    "title": rec["title"],
                    "scheduled_at": proj["scheduled_at"],
                    "duration_minutes": rec["duration_minutes"],
                    "is_projected": True,
                }
            )
            seen.add(key)

    # Sort merged list chronologically so the LLM receives a clean timeline.
    existing_tasks_data.sort(key=lambda x: x["scheduled_at"])

    # 9.4.3 — Load sleep_window and work_hours from user_profile.
    # work_hours may be stored as a natural-language string from onboarding
    # (e.g. "9 AM to 5 PM, Monday to Friday") — pass it through as-is so the
    # LLM can parse it. sleep_window is always a {"start", "end"} dict.
    sleep_window = profile.get("sleep_window", {"start": "22:00", "end": "07:00"})
    work_hours = profile.get("work_hours", "9 AM to 5 PM, Monday to Friday")

    # 9.4.4 — Build slot-finding context
    today_utc = pendulum.now("UTC").format("YYYY-MM-DD")
    context_block = (
        f"\n\nContext:\n"
        f"today_date_utc: {today_utc}\n"
        f"goal_start_date: {goal_start_date or today_utc}\n"
        f"user_timezone: {user_tz}\n"
        f"sleep_window: {json.dumps(sleep_window)}\n"
        f"work_hours: {json.dumps(work_hours)}\n"
        f"existing_tasks: {json.dumps(existing_tasks_data)}\n"
        f"pattern_output: {json.dumps(pattern_output)}\n"
        f"goal_draft: {json.dumps(goal_draft)}\n"
    )

    proposed = goal_draft.get("plan", {}).get("proposed_tasks", [])

    # 9.4.5 — Call validated LLM with SchedulerOutput, max_tokens=1024
    result: SchedulerOutput = await validated_llm_call(
        model=_MODEL,
        system_prompt=_PROMPT + context_block,
        messages=[
            {
                "role": "user",
                "content": f"Find slots for these tasks: {json.dumps(proposed)}",
            }
        ],
        output_model=SchedulerOutput,
        max_tokens=1024,
        user_id=user_id,
    )

    # 9.4.6 — Convert local-time scheduled_at strings to UTC.
    # The prompt instructs the LLM to output naive local-time ISO8601 strings.
    # Strip any accidental Z/offset suffix before parsing as local, to avoid
    # double-conversion if the LLM adds one anyway.
    tz = pendulum.timezone(user_tz)
    converted_slots = []
    for slot in result.slots:
        try:
            dt = _parse_as_local(slot.scheduled_at, tz)
            slot_dict = slot.model_dump()
            slot_dict["scheduled_at"] = dt.in_timezone("UTC").isoformat()
            converted_slots.append(slot_dict)
        except Exception:
            converted_slots.append(slot.model_dump())

    return {
        "scheduler_output": {
            "slots": converted_slots,
            "conflicts": result.conflicts,
            "first_available_start": result.first_available_start,
        }
    }

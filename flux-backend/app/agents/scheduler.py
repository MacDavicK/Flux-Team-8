import json
from pathlib import Path

import pendulum

from app.agents.state import AgentState
from app.models.agent_outputs import SchedulerOutput
from app.services.llm import validated_llm_call
from app.services.supabase import db

# 9.4.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "scheduler.txt").read_text()

_MODEL = "openrouter/openai/gpt-4o-mini"


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

    # 9.4.2 — Query existing pending/rescheduled tasks for the next 6 weeks
    existing_tasks = await db.fetch(
        """
        SELECT title, scheduled_at, duration_minutes
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND scheduled_at >= now()
          AND scheduled_at <= now() + INTERVAL '6 weeks'
        ORDER BY scheduled_at
        """,
        user_id,
    )
    existing_tasks_data = [
        {
            "title": row["title"],
            "scheduled_at": row["scheduled_at"].isoformat(),
            "duration_minutes": row["duration_minutes"],
        }
        for row in existing_tasks
    ]

    # 9.4.3 — Load sleep_window and work_hours from user_profile
    sleep_window = profile.get("sleep_window", {"start": "22:00", "end": "07:00"})
    work_hours = profile.get("work_hours", {"start": "09:00", "end": "17:00"})

    # 9.4.4 — Build slot-finding context
    context_block = (
        f"\n\nContext:\n"
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

    # 9.4.6 — Convert any local-time scheduled_at values to UTC via pendulum
    tz = pendulum.timezone(user_tz)
    converted_slots = []
    for slot in result.slots:
        try:
            dt = pendulum.parse(slot.scheduled_at, tz=tz)
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

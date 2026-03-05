"""
11.1 — task_handler node (§11).

Handles the NEW_TASK intent: extracts task details from the user's message via
LLM, converts the local scheduled time to UTC, and prepares a proposed_task dict
for save_tasks to insert into the database.
"""

from typing import Optional

import pendulum
from pydantic import BaseModel

from app.agents.state import AgentState
from app.services.llm import validated_llm_call

_MODEL = "openrouter/openai/gpt-4o-mini"

_SYSTEM = """\
You are Flux, helping the user schedule a task or reminder.

Extract the task details from the user's latest message and produce a confirmation reply.

FIELD RULES:
- title: concise task title, max 60 characters
- description: one-sentence description of the task
- scheduled_at_local: ISO8601 datetime in the user's LOCAL timezone (e.g. "2026-02-26T17:00:00")
  Set to null only if the user gave no specific time AND no recurrence pattern.
- duration_minutes: estimate if not stated; default 30
- trigger_type: "time" for time-based reminders, "location" for location-triggered reminders
- location_trigger: set only when trigger_type="location" (e.g. "away_from_home"); otherwise null
- recurrence_rule: iCal RRULE string for recurring tasks (e.g. "FREQ=DAILY",
  "FREQ=WEEKLY;BYDAY=MO,WE,FR"); null for one-off tasks
- reply: warm, concise confirmation message that tells the user exactly what was scheduled

RETURN VALID JSON ONLY — no markdown fences, no extra prose.

JSON SCHEMA:
{
  "title": "<string>",
  "description": "<string>",
  "scheduled_at_local": "<ISO8601 or null>",
  "duration_minutes": <int>,
  "trigger_type": "time" | "location",
  "location_trigger": "<string or null>",
  "recurrence_rule": "<RRULE string or null>",
  "reply": "<string>"
}"""


class _TaskExtract(BaseModel):
    title: str
    description: str
    scheduled_at_local: Optional[str] = None
    duration_minutes: int = 30
    trigger_type: str = "time"
    location_trigger: Optional[str] = None
    recurrence_rule: Optional[str] = None
    reply: str


async def task_handler_node(state: AgentState) -> dict:
    """
    11.1 — Handles NEW_TASK intent.

    1. Calls LLM to extract structured task details from the user's message.
    2. Converts scheduled_at from user local time to UTC.
    3. Stores the proposed task in state for save_tasks to write to the database.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}
    history: list[dict] = list(state.get("conversation_history") or [])
    user_tz: str = profile.get("timezone", "UTC")

    now_local = pendulum.now(user_tz).isoformat()
    system = _SYSTEM + f"\n\nUser timezone: {user_tz}\nCurrent local time: {now_local}"

    try:
        result: _TaskExtract = await validated_llm_call(
            model=_MODEL,
            system_prompt=system,
            messages=history,
            output_model=_TaskExtract,
            max_tokens=512,
            user_id=user_id,
        )
    except ValueError:
        fallback = (
            "Sorry, I had trouble parsing those details. "
            "Could you try again? For example: "
            "\"Remind me to take my meds every morning at 8am.\""
        )
        return {
            "conversation_history": history + [
                {"role": "assistant", "content": fallback}
            ],
        }

    # Convert local scheduled_at to UTC
    scheduled_at_utc: Optional[str] = None
    if result.scheduled_at_local:
        try:
            tz = pendulum.timezone(user_tz)
            local_dt = pendulum.parse(result.scheduled_at_local, tz=tz)
            scheduled_at_utc = local_dt.in_timezone("UTC").isoformat()
        except Exception:
            # Fallback: store as-is; the DB insert will handle it
            scheduled_at_utc = result.scheduled_at_local

    proposed_task = {
        "title": result.title,
        "description": result.description,
        "scheduled_at": scheduled_at_utc,
        "duration_minutes": result.duration_minutes,
        "trigger_type": result.trigger_type,
        "location_trigger": result.location_trigger,
        "recurrence_rule": result.recurrence_rule,
        "goal_id": None,
        "shared_with_goal_ids": [],
    }

    return {
        "proposed_tasks": [proposed_task],
        "approval_status": "approved",   # NEW_TASK has no negotiation loop; save immediately
        "conversation_history": history + [
            {"role": "assistant", "content": result.reply}
        ],
    }

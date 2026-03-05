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
  Set to null if the user gave no specific time AND no recurrence pattern, OR if the user is
  being vague (e.g. "some time this week", "not sure", "whenever", "I don't know").
- duration_minutes: estimate if not stated; default 30
- trigger_type: "time" for time-based reminders, "location" for location-triggered reminders
- location_trigger: set only when trigger_type="location" (e.g. "away_from_home"); otherwise null
- recurrence_rule: iCal RRULE string for recurring tasks (e.g. "FREQ=DAILY",
  "FREQ=WEEKLY;BYDAY=MO,WE,FR"); null for one-off tasks
- escalation_policy: controls which notification channels fire if the task is missed.
  Choose one of:
    "silent"     — push notification only. Use for high-frequency recurring tasks
                   (interval < 1 hour: FREQ=MINUTELY, FREQ=HOURLY; or tasks phrased
                   like "every 15 mins", "every 30 mins", "every hour"); ambient
                   reminders; anything the user frames as low-stakes or "quiet".
    "standard"   — push + WhatsApp. Default for most tasks.
    "aggressive" — push + WhatsApp + voice call. Use for appointments, medical tasks,
                   critical deadlines, or one-off tasks where the user implies missing
                   it is unacceptable (e.g. "don't let me forget", "very important").
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
  "escalation_policy": "silent" | "standard" | "aggressive",
  "reply": "<string>"
}"""

# Marker embedded in the ask-for-time question so we can detect it in history
_ASK_TIME_MARKER = "[[ASK_TIME]]"


class _TaskExtract(BaseModel):
    title: str
    description: str
    scheduled_at_local: Optional[str] = None
    duration_minutes: int = 30
    trigger_type: str = "time"
    location_trigger: Optional[str] = None
    recurrence_rule: Optional[str] = None
    escalation_policy: str = "standard"
    reply: str


def _last_assistant_asked_for_time(history: list[dict]) -> bool:
    """Return True if the most recent assistant message was the ask-for-time prompt."""
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            return _ASK_TIME_MARKER in msg.get("content", "")
    return False


async def task_handler_node(state: AgentState) -> dict:
    """
    11.1 — Handles NEW_TASK intent.

    1. Calls LLM to extract structured task details from the user's message.
    2. If no time is extracted and we haven't asked yet, ask ONCE for a specific time.
    3. If no time is extracted and we already asked (user was vague), save as a to-do
       (scheduled_at = None) and confirm it was added to their to-do list.
    4. Converts scheduled_at from user local time to UTC and stores the proposed task.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}
    history: list[dict] = list(state.get("conversation_history") or [])
    user_tz: str = profile.get("timezone", "UTC")

    already_asked = _last_assistant_asked_for_time(history)

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

    # No specific time extracted
    if not result.scheduled_at_local and not result.recurrence_rule:
        if not already_asked:
            # Ask once for a specific time
            ask_msg = (
                f"When would you like to do this — do you have a specific time in mind? {_ASK_TIME_MARKER}"
            )
            return {
                "conversation_history": history + [
                    {"role": "assistant", "content": ask_msg}
                ],
            }
        else:
            # User was vague — save as a to-do with no scheduled_at
            todo_reply = (
                f"Got it! I've added \"{result.title}\" to your to-do list. "
                "You can find it on your home screen whenever you're ready."
            )
            proposed_task = {
                "title": result.title,
                "description": result.description,
                "scheduled_at": None,
                "duration_minutes": result.duration_minutes,
                "trigger_type": result.trigger_type,
                "location_trigger": result.location_trigger,
                "recurrence_rule": None,
                "escalation_policy": result.escalation_policy,
                "goal_id": None,
                "shared_with_goal_ids": [],
            }
            return {
                "proposed_tasks": [proposed_task],
                "approval_status": "approved",
                "conversation_history": history + [
                    {"role": "assistant", "content": todo_reply}
                ],
            }

    # Convert local scheduled_at to UTC.
    # For recurring tasks with no explicit start time, default to now so
    # rrule_expander has a valid dtstart and the poll query can match rows.
    scheduled_at_utc: Optional[str] = None
    start_local_str = result.scheduled_at_local or (
        pendulum.now(user_tz).isoformat() if result.recurrence_rule else None
    )
    if start_local_str:
        try:
            tz = pendulum.timezone(user_tz)
            local_dt = pendulum.parse(start_local_str, tz=tz)
            scheduled_at_utc = local_dt.in_timezone("UTC").isoformat()
        except Exception:
            # Fallback: store as-is; the DB insert will handle it
            scheduled_at_utc = start_local_str

    proposed_task = {
        "title": result.title,
        "description": result.description,
        "scheduled_at": scheduled_at_utc,
        "duration_minutes": result.duration_minutes,
        "trigger_type": result.trigger_type,
        "location_trigger": result.location_trigger,
        "recurrence_rule": result.recurrence_rule,
        "escalation_policy": result.escalation_policy,
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

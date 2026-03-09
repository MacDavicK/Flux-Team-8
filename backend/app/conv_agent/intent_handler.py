"""
Flux Conv Agent -- Intent Handler

Routes Deepgram function-call requests to the appropriate backend
service (goal creation, task creation, task rescheduling).
All DB operations route through the dao_service HTTP API via ConvAgentDaoClient.
"""

from __future__ import annotations

import logging
from typing import Any

from app.conv_agent.dao_client import get_dao_client

logger = logging.getLogger(__name__)


# -- Public Entry Point ------------------------------------------------------


async def handle_intent(
    function_name: str,
    params: dict[str, Any],
    session_id: str,
) -> str:
    """
    Dispatch a Deepgram function call to the correct handler.

    Args:
        function_name: The intent name (e.g. submit_goal_intent).
        params: Extracted parameters from the voice agent LLM.
        session_id: The conversation/session UUID for linking.

    Returns:
        A human-readable confirmation string that is sent back
        to the Deepgram agent for TTS playback.
    """
    handlers = {
        "submit_goal_intent": _handle_goal,
        "submit_new_task_intent": _handle_create_task,
        "submit_reschedule_intent": _handle_reschedule_task,
    }

    handler = handlers.get(function_name)
    if not handler:
        logger.warning("Unknown intent function: %s", function_name)
        return f"Sorry, I don't know how to handle '{function_name}'."

    try:
        return await handler(params, session_id)
    except Exception as exc:
        logger.error(
            "Intent handler failed: function=%s error=%s",
            function_name, exc, exc_info=True,
        )
        return "Something went wrong while processing your request. Please try again."


# -- Goal Intent -------------------------------------------------------------


async def _handle_goal(params: dict[str, Any], session_id: str) -> str:
    """
    Create a new goal from the extracted voice intent.

    Inserts a goal row and links it to the voice conversation.
    """
    goal_statement = params.get("goal_statement", "")
    timeline = params.get("timeline")
    context_notes = params.get("context_notes")

    if not goal_statement:
        return "I need a goal statement to create a goal. Could you tell me what you'd like to achieve?"

    # Build description from optional context
    description = context_notes or ""
    dao_client = get_dao_client()

    # Get user_id from conversation
    user_id = await _get_session_user(session_id)

    # Insert goal via dao_service
    goal = await dao_client.create_goal(
        user_id, goal_statement, _parse_timeline_weeks(timeline), description
    )
    goal_id = goal["id"]

    # Link goal to conversation
    await dao_client.update_conversation_voice(
        session_id,
        extracted_intent="GOAL",
        intent_payload=params,
        linked_goal_id=goal_id,
    )

    logger.info("Goal created: id=%s title=%s", goal_id, goal_statement)

    # Build confirmation for TTS
    timeline_note = f" with a target of {timeline}" if timeline else ""
    return f"Goal created: {goal_statement}{timeline_note}."


# -- Create Task Intent ------------------------------------------------------


async def _handle_create_task(params: dict[str, Any], session_id: str) -> str:
    """
    Create a new standalone task from the extracted voice intent.

    Handles both time-triggered and location-triggered tasks.
    """
    title = params.get("title", "")
    trigger_type = params.get("trigger_type", "time")

    if not title:
        return "I need a task title. What should I remind you about?"

    dao_client = get_dao_client()
    user_id = await _get_session_user(session_id)

    extra_fields: dict[str, Any] = {}

    # Time-triggered fields
    if trigger_type == "time":
        scheduled_at = params.get("scheduled_at")
        if scheduled_at:
            extra_fields["scheduled_at"] = scheduled_at
        recurrence = params.get("recurrence_rule")
        if recurrence:
            extra_fields["recurrence_rule"] = recurrence

    # Location-triggered fields
    if trigger_type == "location":
        location = params.get("location_trigger")
        if location:
            extra_fields["location_trigger"] = location

    task = await dao_client.create_task(user_id, title, trigger_type, **extra_fields)
    task_id = task["id"]

    # Link task to conversation
    await dao_client.update_conversation_voice(
        session_id,
        extracted_intent="NEW_TASK",
        intent_payload=params,
        linked_task_id=task_id,
    )

    logger.info("Task created: id=%s title=%s", task_id, title)
    return f"Task created: {title}."


# -- Reschedule Task Intent --------------------------------------------------


async def _handle_reschedule_task(params: dict[str, Any], session_id: str) -> str:
    """
    Reschedule an existing task based on the extracted voice intent.

    Updates the task's scheduled_at and marks it as rescheduled.
    """
    task_id = params.get("task_id", "")
    new_time = params.get("preferred_new_time")

    if not task_id:
        return "I need to know which task to reschedule. Could you tell me the task?"

    dao_client = get_dao_client()

    # Verify task exists
    task = await dao_client.get_task(task_id)
    if not task:
        return "I couldn't find a task with that ID. Could you double-check?"

    task_title = task["title"]

    # Update the task
    update_fields: dict[str, Any] = {"status": "rescheduled"}
    if new_time:
        update_fields["scheduled_at"] = new_time

    await dao_client.update_task(task_id, **update_fields)

    # Link to conversation
    await dao_client.update_conversation_voice(
        session_id,
        extracted_intent="RESCHEDULE_TASK",
        intent_payload=params,
        linked_task_id=task_id,
    )

    logger.info("Task rescheduled: id=%s", task_id)

    time_note = f" to {new_time}" if new_time else ""
    return f"Rescheduled '{task_title}'{time_note}."


# -- Helpers -----------------------------------------------------------------


async def _get_session_user(session_id: str) -> str:
    """Look up the user_id for a given conversation/session via dao_service."""
    dao_client = get_dao_client()
    conv = await dao_client.get_conversation(session_id)
    return conv["user_id"]


def _parse_timeline_weeks(timeline: str | None) -> int:
    """
    Best-effort parse of a timeline string into a number of weeks.
    Defaults to 6 weeks if parsing fails or timeline is absent.
    """
    if not timeline:
        return 6
    lower = timeline.lower()
    # Simple heuristic: look for a number followed by week/month
    import re
    match = re.search(r"(\d+)\s*(week|month|wk|mo)", lower)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("mo"):
            return num * 4  # rough month-to-weeks
        return num
    return 6

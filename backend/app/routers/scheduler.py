"""
Flux Backend — Scheduler Router

API endpoints for the Scheduler Agent:
  POST /scheduler/suggest  — Get reschedule suggestions for a drifted task
  POST /scheduler/apply    — Apply a reschedule decision or skip
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.agents.scheduler_agent import SchedulerAgent
from app.config import settings
from app.models.schemas import (
    SchedulerApplyRequest,
    SchedulerApplyResponse,
    SchedulerSuggestRequest,
    SchedulerSuggestResponse,
    TaskState,
)
from app.services import scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# Singleton agent instance (stateless — safe to reuse across requests)
_agent = SchedulerAgent()


@router.post("/suggest", response_model=SchedulerSuggestResponse)
async def suggest_reschedule(body: SchedulerSuggestRequest):
    """
    Given a drifted task ID, return 1-2 suggested time slots
    with rationale for each.
    """
    try:
        if settings.scheduler_use_llm_rationale:
            result = await _agent.suggest_slots_with_llm_rationale(body.event_id)
        else:
            result = _agent.suggest_slots(body.event_id)

        return SchedulerSuggestResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scheduler suggest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")


@router.post("/apply", response_model=SchedulerApplyResponse)
async def apply_reschedule(body: SchedulerApplyRequest):
    """
    Apply a reschedule decision:
    - action='reschedule' → update task times, set state='scheduled'
    - action='skip' → set state='missed', preserve future recurrences
    """
    task = scheduler_service.get_task_by_id(body.event_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        if body.action == "skip":
            scheduler_service.mark_task_missed(body.event_id)
            return SchedulerApplyResponse(
                event_id=body.event_id,
                action="skip",
                new_state=TaskState.MISSED,
                message="Task skipped. I'll keep the next occurrence on your schedule.",
            )

        elif body.action == "reschedule":
            if not body.new_start or not body.new_end:
                raise HTTPException(
                    status_code=400,
                    detail="new_start and new_end required for reschedule action",
                )

            scheduler_service.update_task_reschedule(
                task_id=body.event_id,
                new_start=body.new_start,
                new_end=body.new_end,
            )
            time_str = body.new_start.strftime("%-I:%M %p")
            return SchedulerApplyResponse(
                event_id=body.event_id,
                action="reschedule",
                new_state=TaskState.SCHEDULED,
                new_start=body.new_start,
                new_end=body.new_end,
                message=f"Done! Moved to {time_str}. You've got this!",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{body.action}'. Use 'reschedule' or 'skip'.",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler apply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply reschedule")

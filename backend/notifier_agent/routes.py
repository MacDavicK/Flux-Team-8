"""Webhook and demo endpoints for the Notifier Agent (SCRUM-57)."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from dao_service.core.database import DatabaseSession, get_db
from dao_service.schemas.enums import TaskState
from dao_service.schemas.task import TaskUpdateDTO
from dao_service.services.dao_task_service import DaoTaskService

from .models import (
    HealthResponse,
    LocationTriggerRequest,
    NotifierStatusResponse,
    TaskActionRequest,
    TwilioVoiceTwiMLResponse,
    WebhookAckResponse,
)
from .scheduler import get_state_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Notifier Agent"])


# ---------------------------------------------------------------------------
# Dependency: Task Service
# ---------------------------------------------------------------------------

def get_task_service() -> DaoTaskService:
    """Provide a singleton-like instance of the DaoTaskService."""
    return DaoTaskService()


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health():
    """Return the operational status of the Notifier Agent."""
    return {
        "service": "Notifier Agent",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@router.get("/status", response_model=NotifierStatusResponse, summary="Scheduler status")
async def status():
    """Return the current in-memory state of the notification scheduler."""
    registry = get_state_registry()
    return {
        "scheduler_running": True,  # Simplification for MVP
        "pending_task_count": len(registry),
        "tracked_tasks": [s.dict() for s in registry.values()],
    }


# ---------------------------------------------------------------------------
# Twilio Webhooks
# ---------------------------------------------------------------------------

@router.post("/webhooks/twilio/whatsapp", response_model=WebhookAckResponse, summary="Twilio WhatsApp webhook")
async def twilio_whatsapp_webhook(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    task_service: DaoTaskService = Depends(get_task_service),
):
    """Handle incoming WhatsApp replies from users (1/2/3).

    Parses form-encoded data from Twilio.
    """
    form_data = await request.form()
    body = form_data.get("Body", "").strip()
    sender = form_data.get("From", "")

    logger.info("[WEBHOOK] WhatsApp from %s: %s", sender, body)

    # Logic to map '1', '2', '3' back to a specific task would normally
    # involve looking up the 'last sent' task for this phone number.
    # For MVP, we acknowledge the receipt.
    return {
        "success": True,
        "message": f"Received WhatsApp response: {body}",
        "action_taken": "logged",
    }


@router.post("/webhooks/twilio/voice", summary="Twilio Voice TwiML & DTMF handler")
async def twilio_voice_webhook(
    task_id: UUID = Query(...),
    minutes_left: int = Query(0),
    task_title: str = Query("Your task"),
    Digits: str = Query(None),
    db: DatabaseSession = Depends(get_db),
    task_service: DaoTaskService = Depends(get_task_service),
):
    """Serve TwiML for the outbound call and handle DTMF digits.

    DTMF 1 -> done, 2 -> reschedule, 3 -> missed.
    """
    if Digits:
        logger.info("[WEBHOOK] Voice DTMF for task %s: %s", task_id, Digits)
        action = "none"
        if Digits == "1":
            await task_service.update_task(db, task_id=task_id, data=TaskUpdateDTO(state=TaskState.COMPLETED))
            action = "completed"
        elif Digits == "3":
            await task_service.update_task(db, task_id=task_id, data=TaskUpdateDTO(state=TaskState.MISSED))
            action = "missed"

        # Return TwiML to thank and hang up
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'<Say>Thank you. Task has been marked as {action or "acknowledged"}. Goodbye.</Say>'
            '<Hangup/>'
            '</Response>'
        )
        return Response(content=twiml, media_type="application/xml")

    # Initial TwiML for when the user answers
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        f'<Gather numDigits="1" timeout="10" action="/api/webhooks/twilio/voice?task_id={task_id}">'
        f'<Say>Hi! This is your assistant. {task_title} is coming up in {minutes_left} minutes. '
        'Press 1 if you have already done it. '
        'Press 2 if you want to reschedule. '
        'Press 3 to mark it as missed.</Say>'
        '</Gather>'
        '<Say>We didn\'t receive any input. Goodbye.</Say>'
        '</Response>'
    )
    return Response(content=twiml, media_type="application/xml")


# ---------------------------------------------------------------------------
# Task Actions (Internal/App-driven)
# ---------------------------------------------------------------------------

@router.post("/tasks/complete", response_model=WebhookAckResponse, summary="Mark task as done")
async def task_complete(
    req: TaskActionRequest,
    db: DatabaseSession = Depends(get_db),
    task_service: DaoTaskService = Depends(get_task_service),
):
    """Handle the 'Done' CTA from the app."""
    await task_service.update_task(db, task_id=req.task_id, data=TaskUpdateDTO(state=TaskState.COMPLETED))
    return {"success": True, "message": "Task marked as completed", "task_id": str(req.task_id)}


@router.post("/tasks/missed", response_model=WebhookAckResponse, summary="Mark task as missed")
async def task_missed(
    req: TaskActionRequest,
    db: DatabaseSession = Depends(get_db),
    task_service: DaoTaskService = Depends(get_task_service),
):
    """Handle the 'Missed' CTA from the app."""
    await task_service.update_task(db, task_id=req.task_id, data=TaskUpdateDTO(state=TaskState.MISSED))
    return {"success": True, "message": "Task marked as missed", "task_id": str(req.task_id)}


# ---------------------------------------------------------------------------
# Demo: Location Trigger
# ---------------------------------------------------------------------------

@router.post("/demo/location-trigger", response_model=WebhookAckResponse, summary="MVP Location Trigger")
async def location_trigger(
    req: LocationTriggerRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseSession = Depends(get_db),
    task_service: DaoTaskService = Depends(get_task_service),
):
    """Trigger reminders when user leaves home (demo mode)."""
    if not req.is_away:
        return {"success": True, "message": "User is at home. No trigger."}

    logger.info("[DEMO] Location trigger activated for user %s", req.user_id)
    # Fetch tasks with trigger_type = 'location'
    # For MVP, we just acknowledge.
    return {
        "success": True,
        "message": "Location-triggered reminders dispatched (Demo)",
    }


"""Pydantic models for the Notifier Agent (SCRUM-57)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Internal state model (in-memory tracking of sent notifications)
# ---------------------------------------------------------------------------

class NotificationState(BaseModel):
    """Tracks the notification lifecycle for a single task instance."""

    task_id: UUID
    user_id: UUID
    task_title: str
    scheduled_at: datetime
    reminder_sent_at: Optional[datetime] = None
    whatsapp_sent_at: Optional[datetime] = None
    call_sent_at: Optional[datetime] = None
    missed_at: Optional[datetime] = None
    consecutive_miss_count: int = 0
    acknowledged: bool = False


# ---------------------------------------------------------------------------
# Webhook request / response bodies
# ---------------------------------------------------------------------------

class TwilioWhatsAppWebhookPayload(BaseModel):
    """Incoming Twilio WhatsApp reply payload (form-encoded, mapped to model)."""

    From: str = Field(..., description="Sender WhatsApp number (e.g. whatsapp:+14155238886)")
    Body: str = Field(..., description="Raw reply body from the user")
    MessageSid: Optional[str] = None
    AccountSid: Optional[str] = None


class TwilioVoiceWebhookPayload(BaseModel):
    """Incoming Twilio Voice DTMF response payload."""

    CallSid: str = Field(..., description="Unique Twilio call SID")
    Digits: Optional[str] = Field(None, description="DTMF digits pressed by the user (1, 2, or 3)")
    To: Optional[str] = None
    From: Optional[str] = None


class TaskActionRequest(BaseModel):
    """Generic in-app task action (done / missed / reschedule)."""

    task_id: UUID = Field(..., description="UUID of the task being acted upon")
    user_id: Optional[UUID] = Field(None, description="UUID of the acting user")
    note: Optional[str] = Field(None, description="Optional freeform note")


class LocationTriggerRequest(BaseModel):
    """Payload for the demo location-trigger endpoint."""

    user_id: UUID = Field(..., description="UUID of the user who left home")
    is_away: bool = Field(..., description="True when the user activates \"I'm away from home\"")


# ---------------------------------------------------------------------------
# API response envelopes
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Standard health-check response."""

    service: str
    version: str
    status: str
    docs: str
    redoc: str
    openapi: str


class WebhookAckResponse(BaseModel):
    """Generic acknowledgement returned from webhook handlers."""

    success: bool
    message: str
    task_id: Optional[str] = None
    action_taken: Optional[str] = None


class NotifierStatusResponse(BaseModel):
    """Real-time status of the background scheduler."""

    scheduler_running: bool
    pending_task_count: int
    tracked_tasks: List[Dict[str, Any]]


class TwilioVoiceTwiMLResponse(BaseModel):
    """TwiML XML returned to Twilio for ongoing call control."""

    twiml_xml: str

"""Webhooks API endpoints — §17.7"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from app.config import settings
from app.services.supabase import db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def validate_twilio_signature(request: Request) -> dict:
    """17.7.1 — Reject with HTTP 403 on invalid Twilio signature."""
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data)
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return params


@router.post("/twilio/whatsapp")
async def twilio_whatsapp_webhook(params: dict = Depends(validate_twilio_signature)) -> Response:
    """17.7.2 — Parse WhatsApp reply and update task status."""
    body_text = (params.get("Body") or "").strip().lower()
    sender_phone = params.get("WaId") or params.get("From", "").replace("whatsapp:", "")
    message_sid = params.get("MessageSid", "")

    twiml = MessagingResponse()

    # Idempotency check
    existing_log = await db.fetchrow(
        "SELECT id, response FROM notification_log WHERE external_id = $1 AND channel = 'whatsapp'",
        message_sid,
    )
    if existing_log and existing_log["response"] is not None:
        return Response(content=str(twiml), media_type="application/xml")

    # Find user by phone number
    user_row = await db.fetchrow(
        "SELECT id FROM users WHERE notification_preferences->>'phone_number' = $1",
        sender_phone,
    )
    if user_row is None:
        twiml.message("Sorry, we could not find your account.")
        return Response(content=str(twiml), media_type="application/xml")

    # Find task linked to this MessageSid
    log_row = await db.fetchrow(
        "SELECT task_id FROM notification_log WHERE external_id = $1 AND channel = 'whatsapp'",
        message_sid,
    )
    if log_row is None:
        twiml.message("Sorry, we could not find the task associated with this message.")
        return Response(content=str(twiml), media_type="application/xml")

    task_id = str(log_row["task_id"])
    response_label: str

    if body_text in ("1", "done"):
        await db.execute("UPDATE tasks SET status = 'done', completed_at = now() WHERE id = $1", task_id)
        response_label = "done"
        twiml.message("Great work! Task marked as done.")
    elif body_text in ("2", "reschedule"):
        response_label = "reschedule"
        twiml.message(f"To reschedule, open the Flux app: flux://tasks/{task_id}")
    elif body_text in ("3", "missed"):
        await db.execute("UPDATE tasks SET status = 'missed' WHERE id = $1", task_id)
        response_label = "missed"
        twiml.message("Task marked as missed. We'll help you reschedule.")
    else:
        response_label = "unknown"
        twiml.message("Reply 1 (done), 2 (reschedule), or 3 (missed).")

    await db.execute(
        "UPDATE notification_log SET response = $2, responded_at = now() WHERE external_id = $1 AND channel = 'whatsapp'",
        message_sid, response_label,
    )

    return Response(content=str(twiml), media_type="application/xml")


@router.post("/twilio/voice")
async def twilio_voice_webhook(task_id: str = Query(...), params: dict = Depends(validate_twilio_signature)) -> Response:
    """17.7.3 — Parse DTMF digits and update task status."""
    digits = (params.get("Digits") or "").strip()
    call_sid = params.get("CallSid", "")

    twiml = VoiceResponse()

    # Idempotency check
    existing_log = await db.fetchrow(
        "SELECT id, response FROM notification_log WHERE external_id = $1 AND channel = 'call'",
        call_sid,
    )
    if existing_log and existing_log["response"] is not None:
        twiml.say("Thank you. Goodbye.")
        twiml.hangup()
        return Response(content=str(twiml), media_type="application/xml")

    response_label: str
    if digits == "1":
        await db.execute("UPDATE tasks SET status = 'done', completed_at = now() WHERE id = $1", task_id)
        response_label = "done"
    elif digits == "2":
        response_label = "reschedule"
    elif digits == "3":
        await db.execute("UPDATE tasks SET status = 'missed' WHERE id = $1", task_id)
        response_label = "missed"
    else:
        response_label = "unknown"

    await db.execute(
        "UPDATE notification_log SET response = $2, responded_at = now() WHERE external_id = $1 AND channel = 'call'",
        call_sid, response_label,
    )

    twiml.say("Thank you. Goodbye.")
    twiml.hangup()
    return Response(content=str(twiml), media_type="application/xml")

"""Webhooks API endpoints — §17.7"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse

from app.config import settings
from app.services.supabase import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _get_webhook_url_for_signature(request: Request) -> str:
    """
    Twilio signs with the public HTTPS URL. Behind ngrok, request.url is http://.
    Reconstruct the URL Twilio used for signature validation.
    """
    url = str(request.url)
    if url.startswith("http://") and settings.twilio_webhook_base_url.startswith("https://"):
        base = settings.twilio_webhook_base_url.rstrip("/")
        path = request.url.path
        query = request.url.query
        url = f"{base}{path}" + (f"?{query}" if query else "")
    return url


async def validate_twilio_signature(request: Request) -> dict:
    """17.7.1 — Reject with HTTP 403 on invalid Twilio signature."""
    try:
        validator = RequestValidator(settings.twilio_auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = _get_webhook_url_for_signature(request)
        form_data = await request.form()
        params = {k: (v[0] if isinstance(v, list) else v) for k, v in dict(form_data).items()}
        if not validator.validate(url, params, signature):
            logger.warning("Twilio webhook: invalid signature for url=%s", url)
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        return params
    except HTTPException:
        raise
    except Exception:
        logger.exception("Twilio webhook signature validation error: %s", traceback.format_exc())
        raise


@router.post("/twilio/whatsapp")
async def twilio_whatsapp_webhook(
    params: dict = Depends(validate_twilio_signature),
) -> Response:
    """17.7.2 — Parse WhatsApp reply and update task status."""
    try:
        return await _twilio_whatsapp_webhook_impl(params)
    except Exception:
        logger.exception("WhatsApp webhook error: %s", traceback.format_exc())
        raise


def _normalize_phone(phone: str) -> str:
    """Normalize phone for matching: strip + and spaces, keep digits only."""
    if not phone:
        return ""
    return "".join(c for c in phone if c.isdigit()) or phone


async def _twilio_whatsapp_webhook_impl(params: dict) -> Response:
    """Implementation of WhatsApp webhook handler."""
    body_text = (params.get("Body") or "").strip().lower()
    sender_phone_raw = params.get("WaId") or params.get("From", "").replace("whatsapp:", "")
    sender_phone = _normalize_phone(sender_phone_raw)
    message_sid = params.get("MessageSid", "")

    logger.info(
        "WhatsApp webhook received: MessageSid=%s From=%s Body=%r",
        message_sid,
        sender_phone_raw,
        body_text,
    )

    twiml = MessagingResponse()

    # Idempotency check (incoming MessageSid may differ from our outbound SID)
    existing_log = await db.fetchrow(
        "SELECT id, response FROM notification_log WHERE external_id = $1 AND channel = 'whatsapp'",
        message_sid,
    )
    if existing_log and existing_log["response"] is not None:
        logger.info("WhatsApp webhook: idempotent skip (already processed MessageSid=%s)", message_sid)
        return Response(content=str(twiml), media_type="application/xml")

    # Find user by phone number (match normalized: digits only, handles +91 vs 91 vs 919876543210)
    user_row = await db.fetchrow(
        """
        SELECT id FROM users
        WHERE REGEXP_REPLACE(COALESCE(notification_preferences->>'phone_number', ''), '[^0-9]', '', 'g') = $1
        """,
        sender_phone,
    )
    if user_row is None:
        logger.warning("WhatsApp webhook: user not found for phone=%s", sender_phone)
        twiml.message("Sorry, we could not find your account.")
        return Response(content=str(twiml), media_type="application/xml")

    # Find task: first by MessageSid (our outbound SID), then fallback to most recent pending for this user
    log_row = await db.fetchrow(
        "SELECT task_id FROM notification_log WHERE external_id = $1 AND channel = 'whatsapp'",
        message_sid,
    )
    if log_row is None:
        log_row = await db.fetchrow(
            """
            SELECT nl.task_id FROM notification_log nl
            JOIN tasks t ON t.id = nl.task_id
            WHERE nl.channel = 'whatsapp' AND nl.response IS NULL
              AND t.user_id = $1 AND t.status = 'pending'
            ORDER BY nl.sent_at DESC
            LIMIT 1
            """,
            user_row["id"],
        )
        if log_row:
            logger.info(
                "WhatsApp webhook: matched task by user fallback (incoming MessageSid=%s)",
                message_sid,
            )

    if log_row is None:
        logger.warning("WhatsApp webhook: no pending task found for user phone=%s", sender_phone)
        twiml.message("Sorry, we could not find the task associated with this message.")
        return Response(content=str(twiml), media_type="application/xml")

    task_id = str(log_row["task_id"])
    response_label: str

    if body_text in ("1", "done"):
        await db.execute(
            "UPDATE tasks SET status = 'done', completed_at = now() WHERE id = $1",
            task_id,
        )
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
        response_label = "no_response"  # DB constraint: unknown replies stored as no_response
        twiml.message("Reply 1 (done), 2 (reschedule), or 3 (missed).")

    await db.execute(
        "UPDATE notification_log SET response = $2, responded_at = now() WHERE task_id = $1 AND channel = 'whatsapp' AND response IS NULL",
        task_id,
        response_label,
    )

    logger.info(
        "WhatsApp webhook: task_id=%s response_label=%s reply=%r",
        task_id,
        response_label,
        body_text,
    )
    return Response(content=str(twiml), media_type="application/xml")


@router.post("/twilio/voice")
async def twilio_voice_webhook(
    task_id: str = Query(...), params: dict = Depends(validate_twilio_signature)
) -> Response:
    """17.7.3 — Parse DTMF digits and update task status."""
    digits = (params.get("Digits") or "").strip()
    call_sid = params.get("CallSid", "")

    logger.info(
        "Voice webhook received: CallSid=%s task_id=%s Digits=%r",
        call_sid,
        task_id,
        digits,
    )

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
        await db.execute(
            "UPDATE tasks SET status = 'done', completed_at = now() WHERE id = $1",
            task_id,
        )
        response_label = "done"
    elif digits == "2":
        response_label = "reschedule"
    elif digits == "3":
        await db.execute("UPDATE tasks SET status = 'missed' WHERE id = $1", task_id)
        response_label = "missed"
    else:
        response_label = "no_response"  # DB constraint: unknown digits stored as no_response

    await db.execute(
        "UPDATE notification_log SET response = $2, responded_at = now() WHERE external_id = $1 AND channel = 'call'",
        call_sid,
        response_label,
    )

    logger.info(
        "Voice webhook: CallSid=%s task_id=%s response_label=%s",
        call_sid,
        task_id,
        response_label,
    )
    twiml.say("Thank you. Goodbye.")
    twiml.hangup()
    return Response(content=str(twiml), media_type="application/xml")

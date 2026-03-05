"""
14.2 — Twilio Service (app/services/twilio_service.py) — §9

WhatsApp + Voice call notifications via Twilio, plus OTP via Twilio Verify.
"""
from __future__ import annotations

from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.config import settings

# 14.2.1 — Twilio client singleton
_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

_WHATSAPP_TEMPLATE = (
    "⏰ *Flux Reminder*\n"
    "Your task is due: *{title}*\n\n"
    "Reply with:\n"
    "1️⃣ Done\n"
    "2️⃣ Reschedule\n"
    "3️⃣ Missed"
)


async def dispatch_whatsapp(task: dict) -> str:
    """
    14.2.2 — Send a WhatsApp message reminder.

    Gates:
    - user must have phone_verified = true
    - user must have whatsapp_opt_in_at IS NOT NULL

    Phone number is stored in notification_preferences->>'phone_number'.
    Returns MessageSid.
    """
    from app.services.supabase import db  # late import to avoid circular

    user_id = str(task.get("user_id", ""))
    user = await db.fetchrow(
        """
        SELECT phone_verified, whatsapp_opt_in_at,
               notification_preferences->>'phone_number' AS phone_number
        FROM users WHERE id = $1
        """,
        user_id,
    )

    if not user or not user["phone_verified"] or not user["whatsapp_opt_in_at"]:
        raise ValueError(f"User {user_id} not eligible for WhatsApp notifications")

    phone = user["phone_number"]
    if not phone:
        raise ValueError(f"User {user_id} has no phone number on record")

    body = _WHATSAPP_TEMPLATE.format(title=task.get("title", "Task"))

    msg = _client.messages.create(
        from_=f"whatsapp:{settings.twilio_whatsapp_from}",
        to=f"whatsapp:{phone}",
        body=body,
    )
    return msg.sid


async def dispatch_call(task: dict) -> str:
    """
    14.2.3 — Initiate a voice call with DTMF gather.

    Gates on phone_verified = true.
    Builds TwiML <Gather> with DTMF digits 1/2/3.
    Returns CallSid.
    """
    from app.services.supabase import db  # late import to avoid circular

    user_id = str(task.get("user_id", ""))
    task_id = str(task.get("id", ""))

    user = await db.fetchrow(
        """
        SELECT phone_verified,
               notification_preferences->>'phone_number' AS phone_number
        FROM users WHERE id = $1
        """,
        user_id,
    )

    if not user or not user["phone_verified"]:
        raise ValueError(f"User {user_id} not eligible for voice call notifications")

    phone = user["phone_number"]
    if not phone:
        raise ValueError(f"User {user_id} has no phone number on record")

    # 14.2.3 — Build TwiML
    response = VoiceResponse()
    callback_url = (
        f"{settings.twilio_webhook_base_url}/api/v1/webhooks/twilio/voice"
        f"?task_id={task_id}"
    )
    gather = Gather(num_digits=1, action=callback_url, method="POST")
    gather.say(
        f"This is Flux. Your task {task.get('title', '')} is due. "
        "Press 1 for done. Press 2 to reschedule. Press 3 to mark as missed."
    )
    response.append(gather)
    response.say("We did not receive your input. Goodbye.")

    call = _client.calls.create(
        from_=settings.twilio_voice_from,
        to=phone,
        twiml=str(response),
    )
    return call.sid


async def send_otp(phone_number: str) -> None:
    """14.2.4 — Send an OTP via Twilio Verify (SMS channel)."""
    _client.verify.v2.services(
        settings.twilio_verify_service_sid
    ).verifications.create(to=phone_number, channel="sms")


async def confirm_otp(phone_number: str, code: str) -> bool:
    """14.2.5 — Verify OTP code. Returns True if approved."""
    check = _client.verify.v2.services(
        settings.twilio_verify_service_sid
    ).verification_checks.create(to=phone_number, code=code)
    return check.status == "approved"

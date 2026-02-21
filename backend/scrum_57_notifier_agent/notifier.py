"""Notification dispatchers: push, WhatsApp, and Twilio Voice (SCRUM-57).

All senders are pure functions; they own no state.  The scheduler
calls them and records timestamps in its in-memory NotificationState.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Twilio helpers
# ---------------------------------------------------------------------------

def _get_twilio_client() -> Client:
    """Build a Twilio REST client from environment variables."""
    return Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )


def _minutes_left(scheduled_at: datetime) -> int:
    """Return non-negative integer minutes between now and scheduled_at."""
    delta = scheduled_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds() / 60))


# ---------------------------------------------------------------------------
# Channel 1 – Push notification (Supabase Realtime / Web Push)
# ---------------------------------------------------------------------------

def send_push_notification(
    task_id: UUID,
    task_title: str,
    scheduled_at: datetime,
    user_id: UUID,
) -> bool:
    """Broadcast a push reminder via Supabase Realtime.

    MVP: logs the payload and returns True.  Wire supabase-py
    realtime channel once the frontend service-worker is registered.

    Args:
        task_id: UUID of the task.
        task_title: Human-readable task name.
        scheduled_at: UTC scheduled time of the task.
        user_id: UUID of the task owner.

    Returns:
        True on success, False on failure.
    """
    try:
        mins = _minutes_left(scheduled_at)
        payload = {
            "type": "push_reminder",
            "task_id": str(task_id),
            "user_id": str(user_id),
            "task_title": task_title,
            "minutes_left": mins,
            "actions": ["done", "reschedule", "missed"],
        }
        # TODO: replace with supabase_py realtime channel.send()
        logger.info(
            "[PUSH] Dispatching | task_id=%s user_id=%s minutes_left=%d",
            task_id, user_id, mins,
        )
        logger.debug("[PUSH] Payload: %s", payload)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("[PUSH] Failed | task_id=%s error=%s", task_id, exc)
        return False


# ---------------------------------------------------------------------------
# Channel 2 – WhatsApp via Twilio WhatsApp Business API
# ---------------------------------------------------------------------------

def send_whatsapp_notification(
    task_id: UUID,
    task_title: str,
    scheduled_at: datetime,
    user_phone: str,
    reschedule_available: bool = False,
) -> bool:
    """Send a WhatsApp escalation message via Twilio.

    Args:
        task_id: UUID of the task.
        task_title: Human-readable task name.
        scheduled_at: UTC scheduled time of the task.
        user_phone: Recipient E.164 phone number.
        reschedule_available: Whether a reschedule slot exists later today.

    Returns:
        True on success, False on failure.
    """
    from_wa = f"whatsapp:{os.environ['TWILIO_WHATSAPP_FROM']}"
    to_wa = f"whatsapp:{user_phone}"
    mins = _minutes_left(scheduled_at)

    lines = [
        f"Hi! This is your assistant. *{task_title}* is coming up in {mins} minute(s).",
        "",
        "Reply with:",
        "*1* – Mark as Done",
    ]
    if reschedule_available:
        lines.append("*2* – Reschedule")
    lines.append("*3* – Mark as Missed")
    body = "\n".join(lines)

    try:
        client = _get_twilio_client()
        msg = client.messages.create(from_=from_wa, to=to_wa, body=body)
        logger.info(
            "[WHATSAPP] Sent | task_id=%s sid=%s to=%s",
            task_id, msg.sid, to_wa,
        )
        return True
    except TwilioRestException as exc:
        logger.error(
            "[WHATSAPP] Twilio error | task_id=%s code=%s msg=%s",
            task_id, exc.code, exc.msg,
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("[WHATSAPP] Unexpected error | task_id=%s error=%s", task_id, exc)
        return False


# ---------------------------------------------------------------------------
# Channel 3 – Phone call via Twilio Programmable Voice (TTS + DTMF)
# ---------------------------------------------------------------------------

def send_phone_call(
    task_id: UUID,
    task_title: str,
    scheduled_at: datetime,
    user_phone: str,
    webhook_base_url: str,
) -> Optional[str]:
    """Initiate a Twilio outbound call with TTS script and DTMF handling.

    DTMF map:
        1 -> done
        2 -> reschedule (opens chat deep-link)
        3 -> missed

    Args:
        task_id: UUID of the task.
        task_title: Human-readable task name.
        scheduled_at: UTC scheduled time of the task.
        user_phone: Destination E.164 phone number.
        webhook_base_url: Public base URL for TwiML callback.

    Returns:
        Twilio call SID on success, None on failure.
    """
    mins = _minutes_left(scheduled_at)
    twiml_url = (
        f"{webhook_base_url.rstrip('/')}/api/webhooks/twilio/voice"
        f"?task_id={task_id}&minutes_left={mins}&task_title={task_title}"
    )
    try:
        client = _get_twilio_client()
        call = client.calls.create(
            from_=os.environ["TWILIO_PHONE_NUMBER"],
            to=user_phone,
            url=twiml_url,
            method="POST",
        )
        logger.info(
            "[CALL] Initiated | task_id=%s sid=%s to=%s",
            task_id, call.sid, user_phone,
        )
        return call.sid
    except TwilioRestException as exc:
        logger.error(
            "[CALL] Twilio error | task_id=%s code=%s msg=%s",
            task_id, exc.code, exc.msg,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("[CALL] Unexpected error | task_id=%s error=%s", task_id, exc)
        return None


# ---------------------------------------------------------------------------
# Pattern Observer hook
# ---------------------------------------------------------------------------

def notify_pattern_observer(
    task_id: UUID,
    user_id: UUID,
    consecutive_miss_count: int,
) -> None:
    """Fire an event when a task accumulates 3+ consecutive misses in the same slot.

    Replace with a real event dispatch (Supabase realtime / internal queue)
    once the Pattern Observer agent is implemented.

    Args:
        task_id: UUID of the missed task.
        user_id: UUID of the task owner.
        consecutive_miss_count: Number of back-to-back misses detected.
    """
    logger.warning(
        "[PATTERN_OBSERVER] Repeated miss | task_id=%s user_id=%s misses=%d",
        task_id,
        user_id,
        consecutive_miss_count,
    )
    # TODO: emit event to Pattern Observer agent.

"""
14.1 — Push Service (app/services/push_service.py) — §9

Sends Web Push notifications using pywebpush + VAPID keys.
"""
from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush

from app.config import settings

logger = logging.getLogger(__name__)


async def dispatch_push(task: dict, user_push_subscription: dict) -> bool:
    """
    14.1.1 — Send a Web Push notification for a task.

    14.1.2 — Payload includes title, body, task_id, and 3 action buttons.
    14.1.3 — Uses VAPID private key and claims email from settings.
    14.1.4 — WebPushException is caught and logged; does not re-raise.

    Returns True if dispatch succeeded, False otherwise.
    """
    task_id = str(task.get("id", ""))
    title = task.get("title", "Task Reminder")
    scheduled_at = task.get("scheduled_at", "")

    payload = {
        "title": title,
        "body": f"Your task is due: {title}",
        "task_id": task_id,
        "actions": [
            {"action": "done",       "title": "✓ Done"},
            {"action": "reschedule", "title": "⏰ Reschedule"},
            {"action": "missed",     "title": "✗ Missed"},
        ],
        "scheduled_at": str(scheduled_at),
    }

    try:
        webpush(
            subscription_info=user_push_subscription,
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={
                "sub": f"mailto:{settings.vapid_claims_email}",
            },
        )
        return True
    except WebPushException as exc:
        # 14.1.4 — Expired / invalid subscriptions are non-fatal
        logger.warning(
            "Web push failed for task %s: %s",
            task_id,
            exc,
            exc_info=False,
        )
        return False

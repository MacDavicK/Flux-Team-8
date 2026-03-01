"""
15.3 — Recovery for stuck dispatch_log entries.
"""
from __future__ import annotations

import logging

from app.services.push_service import dispatch_push
from app.services.supabase import db
from app.services.twilio_service import dispatch_call, dispatch_whatsapp

logger = logging.getLogger(__name__)


async def recover_stuck_dispatches() -> None:
    """
    15.3.1 — Query dispatch_log WHERE status='pending' AND created_at < now()-5min.
    Re-attempt dispatch for each stuck entry.
    """
    stuck = await db.fetch(
        """
        SELECT dl.id AS log_id, dl.task_id, dl.channel,
               t.user_id, t.title, t.scheduled_at,
               u.push_subscription
        FROM dispatch_log dl
        JOIN tasks t ON t.id = dl.task_id
        JOIN users u ON u.id = t.user_id
        WHERE dl.status = 'pending'
          AND dl.created_at < now() - INTERVAL '5 minutes'
        """,
    )

    recovered = 0
    for row in stuck:
        task_id = str(row["task_id"])
        channel = row["channel"]
        task = dict(row)

        try:
            if channel == "push":
                push_sub = row["push_subscription"]
                if push_sub:
                    await dispatch_push(task, push_sub)
            elif channel == "whatsapp":
                await dispatch_whatsapp(task)
            elif channel == "call":
                await dispatch_call(task)
            # auto_miss requires no external dispatch

            await db.execute(
                "UPDATE dispatch_log SET status = 'dispatched', dispatched_at = now() WHERE task_id = $1 AND channel = $2 AND status = 'pending'",
                task_id, channel,
            )
            recovered += 1
        except Exception as exc:
            logger.warning("Recovery failed for task %s channel %s: %s", task_id, channel, exc)
            await db.execute(
                "UPDATE dispatch_log SET status = 'failed', error = $3 WHERE task_id = $1 AND channel = $2 AND status = 'pending'",
                task_id, channel, str(exc),
            )

    if recovered:
        logger.info("Recovered %d stuck dispatches", recovered)

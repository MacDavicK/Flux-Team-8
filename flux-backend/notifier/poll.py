"""
15.2 — Notification poll loop.

Four-step escalation cycle:
  1. Push reminders for tasks due soon
  2. WhatsApp escalation
  3. Voice call escalation
  4. Auto-miss marking
"""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.services.push_service import dispatch_push
from app.services.supabase import db
from app.services.twilio_service import dispatch_call, dispatch_whatsapp

logger = logging.getLogger(__name__)


async def notification_poll() -> None:
    """Main poll function called by APScheduler on each interval."""
    try:
        await _step_push()
        await _step_whatsapp()
        await _step_call()
        await _step_auto_miss()
    except Exception as exc:
        logger.exception("notification_poll error: %s", exc)


# ─────────────────────────────────────────────────────────────────
# Step 1 — Push reminders
# ─────────────────────────────────────────────────────────────────

async def _step_push() -> None:
    """15.2.1 — Push reminders for tasks due within reminder_lead_minutes."""
    lead = settings.reminder_lead_minutes
    rows = await db.fetch(
        f"""
        SELECT t.id, t.user_id, t.title, t.scheduled_at, u.push_subscription
        FROM tasks t
        JOIN users u ON u.id = t.user_id
        WHERE t.status = 'pending'
          AND t.trigger_type = 'time'
          AND t.reminder_sent_at IS NULL
          AND t.scheduled_at <= now() + ('{lead} minutes')::interval
          AND t.scheduled_at > now() - INTERVAL '1 hour'
        """,
    )

    for row in rows:
        task_id = str(row["id"])
        # 15.2.2 — Atomic CAS: only proceed if we claim the row
        claimed = await db.fetchval(
            "UPDATE tasks SET reminder_sent_at = now() WHERE id = $1 AND reminder_sent_at IS NULL RETURNING id",
            task_id,
        )
        if claimed is None:
            continue  # Another worker claimed it first

        push_sub = row["push_subscription"]
        if not push_sub:
            continue

        await log_dispatch(task_id, "push")
        try:
            await dispatch_push(dict(row), push_sub)
            await mark_dispatch_done(task_id, "push")
        except Exception as exc:
            logger.warning("Push dispatch failed for task %s: %s", task_id, exc)
            await _mark_dispatch_failed(task_id, "push", str(exc))


# ─────────────────────────────────────────────────────────────────
# Step 2 — WhatsApp escalation
# ─────────────────────────────────────────────────────────────────

async def _step_whatsapp() -> None:
    """15.2.3 — WhatsApp for tasks where push sent > escalation_window ago."""
    esc = settings.escalation_window_minutes
    rows = await db.fetch(
        f"""
        SELECT id, user_id, title, scheduled_at FROM tasks
        WHERE status = 'pending'
          AND reminder_sent_at IS NOT NULL
          AND whatsapp_sent_at IS NULL
          AND reminder_sent_at <= now() - ('{esc} minutes')::interval
        """,
    )

    for row in rows:
        task_id = str(row["id"])
        # 15.2.4 — Atomic CAS on whatsapp_sent_at
        claimed = await db.fetchval(
            "UPDATE tasks SET whatsapp_sent_at = now() WHERE id = $1 AND whatsapp_sent_at IS NULL RETURNING id",
            task_id,
        )
        if claimed is None:
            continue

        await log_dispatch(task_id, "whatsapp")
        try:
            message_sid = await dispatch_whatsapp(dict(row))
            await mark_dispatch_done(task_id, "whatsapp", external_id=message_sid)
        except Exception as exc:
            logger.warning("WhatsApp dispatch failed for task %s: %s", task_id, exc)
            await _mark_dispatch_failed(task_id, "whatsapp", str(exc))


# ─────────────────────────────────────────────────────────────────
# Step 3 — Voice call escalation
# ─────────────────────────────────────────────────────────────────

async def _step_call() -> None:
    """15.2.5 — Voice call for tasks where whatsapp sent > escalation_window ago."""
    esc = settings.escalation_window_minutes
    rows = await db.fetch(
        f"""
        SELECT id, user_id, title, scheduled_at FROM tasks
        WHERE status = 'pending'
          AND whatsapp_sent_at IS NOT NULL
          AND call_sent_at IS NULL
          AND whatsapp_sent_at <= now() - ('{esc} minutes')::interval
        """,
    )

    for row in rows:
        task_id = str(row["id"])
        # 15.2.6 — Atomic CAS on call_sent_at
        claimed = await db.fetchval(
            "UPDATE tasks SET call_sent_at = now() WHERE id = $1 AND call_sent_at IS NULL RETURNING id",
            task_id,
        )
        if claimed is None:
            continue

        await log_dispatch(task_id, "call")
        try:
            call_sid = await dispatch_call(dict(row))
            await mark_dispatch_done(task_id, "call", external_id=call_sid)
        except Exception as exc:
            logger.warning("Call dispatch failed for task %s: %s", task_id, exc)
            await _mark_dispatch_failed(task_id, "call", str(exc))


# ─────────────────────────────────────────────────────────────────
# Step 4 — Auto-miss
# ─────────────────────────────────────────────────────────────────

async def _step_auto_miss() -> None:
    """15.2.7 — Mark tasks as missed when call sent > escalation_window ago."""
    esc = settings.escalation_window_minutes
    rows = await db.fetch(
        f"""
        SELECT id, user_id FROM tasks
        WHERE status = 'pending'
          AND call_sent_at IS NOT NULL
          AND call_sent_at <= now() - ('{esc} minutes')::interval
        """,
    )

    for row in rows:
        task_id = str(row["id"])
        user_id = str(row["user_id"])
        claimed = await db.fetchval(
            "UPDATE tasks SET status = 'missed' WHERE id = $1 AND status = 'pending' RETURNING id",
            task_id,
        )
        if claimed is None:
            continue

        await log_dispatch(task_id, "auto_miss")
        await mark_dispatch_done(task_id, "auto_miss")
        asyncio.create_task(check_and_flag_miss_pattern(user_id, task_id))


# ─────────────────────────────────────────────────────────────────
# Dispatch log helpers
# ─────────────────────────────────────────────────────────────────

async def log_dispatch(task_id: str, channel: str) -> None:
    """15.2.8 — Insert dispatch_log row with status='pending'."""
    try:
        await db.execute(
            "INSERT INTO dispatch_log (task_id, channel, status) VALUES ($1, $2, 'pending')",
            task_id, channel,
        )
    except Exception as exc:
        logger.warning("log_dispatch failed: %s", exc)


async def mark_dispatch_done(task_id: str, channel: str, external_id: str | None = None) -> None:
    """15.2.9 — Update dispatch_log to dispatched; insert notification_log."""
    try:
        await db.execute(
            "UPDATE dispatch_log SET status = 'dispatched', dispatched_at = now() WHERE task_id = $1 AND channel = $2 AND status = 'pending'",
            task_id, channel,
        )
        if external_id:
            await db.execute(
                "INSERT INTO notification_log (task_id, channel, external_id) VALUES ($1, $2, $3)",
                task_id, channel, external_id,
            )
    except Exception as exc:
        logger.warning("mark_dispatch_done failed: %s", exc)


async def _mark_dispatch_failed(task_id: str, channel: str, error: str) -> None:
    try:
        await db.execute(
            "UPDATE dispatch_log SET status = 'failed', error = $3 WHERE task_id = $1 AND channel = $2 AND status = 'pending'",
            task_id, channel, error,
        )
    except Exception as exc:
        logger.warning("_mark_dispatch_failed failed: %s", exc)


# ─────────────────────────────────────────────────────────────────
# Pattern miss signal
# ─────────────────────────────────────────────────────────────────

async def check_and_flag_miss_pattern(user_id: str, task_id: str) -> None:
    """15.2.10 — Check for ≥3 consecutive misses in same slot; log if threshold met."""
    try:
        # Check if the missed task has ≥3 consecutive misses in the same day-of-week/hour
        result = await db.fetchval(
            """
            WITH missed AS (
                SELECT DATE_TRUNC('hour', scheduled_at) AS slot_hour,
                       EXTRACT(DOW FROM scheduled_at) AS dow,
                       EXTRACT(HOUR FROM scheduled_at) AS hour,
                       scheduled_at::date AS day
                FROM tasks
                WHERE user_id = $1
                  AND status = 'missed'
                  AND scheduled_at >= now() - INTERVAL '4 weeks'
            ),
            this_task AS (
                SELECT EXTRACT(DOW FROM scheduled_at) AS dow,
                       EXTRACT(HOUR FROM scheduled_at) AS hour
                FROM tasks WHERE id = $2
            )
            SELECT COUNT(*) FROM missed m, this_task t
            WHERE m.dow = t.dow
              AND ABS(m.hour - t.hour) <= 1
            """,
            user_id, task_id,
        )
        if (result or 0) >= 3:
            logger.info(
                "Pattern threshold met for user %s task %s: %d consecutive misses",
                user_id, task_id, result,
            )
    except Exception as exc:
        logger.debug("check_and_flag_miss_pattern error: %s", exc)

"""Background scheduler — APScheduler polling loop (SCRUM-57).

Polls the dao_service every 60 seconds and drives the escalation ladder:
  T - REMINDER_LEAD_MINUTES   -> Push notification
  T + ESCALATION_WINDOW       -> WhatsApp (if push unacknowledged)
  T + 2 x ESCALATION_WINDOW   -> Phone call (if WhatsApp unacknowledged)
  T + 3 x ESCALATION_WINDOW   -> Auto-miss + Pattern Observer

NOTE: The scheduler NEVER accesses the database directly.
All reads/writes go through dao_service.services.dao_task_service.
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dao_service.core.database import DatabaseSession
from dao_service.schemas.enums import TaskState
from dao_service.schemas.task import TaskUpdateDTO
from dao_service.services.dao_task_service import DaoTaskService

from .models import NotificationState
from .notifier import (
    notify_pattern_observer,
    send_phone_call,
    send_push_notification,
    send_whatsapp_notification,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (overridable via environment)
# ---------------------------------------------------------------------------

REMINDER_LEAD_MINUTES: int  = int(os.getenv("REMINDER_LEAD_MINUTES",  "10"))
ESCALATION_WINDOW: int      = int(os.getenv("ESCALATION_WINDOW",      "2"))
POLL_INTERVAL_SECONDS: int  = int(os.getenv("POLL_INTERVAL_SECONDS",  "60"))
CONSECUTIVE_MISS_THRESHOLD = int(os.getenv("CONSECUTIVE_MISS_THRESHOLD", "3"))
WEBHOOK_BASE_URL: str       = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8057")

# ---------------------------------------------------------------------------
# In-memory notification state registry
# Key: task UUID  ->  NotificationState
# ---------------------------------------------------------------------------

_state_registry: Dict[str, NotificationState] = {}

# Singletons injected at startup
_task_service: Optional[DaoTaskService] = None
_db: Optional[DatabaseSession] = None
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Return the singleton AsyncIOScheduler instance."""
    return _scheduler


def get_state_registry() -> Dict[str, NotificationState]:
    """Return the in-memory notification state registry (read-only copy)."""
    return dict(_state_registry)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_terminal(state: TaskState) -> bool:
    """Return True if the task state means escalation should stop."""
    return state in (TaskState.COMPLETED, TaskState.MISSED)


def _get_or_create_state(task) -> NotificationState:
    """Retrieve or create an in-memory NotificationState for a task."""
    key = str(task.id)
    if key not in _state_registry:
        _state_registry[key] = NotificationState(
            task_id=task.id,
            user_id=task.user_id,
            task_title=task.title,
            scheduled_at=task.start_time,
        )
        logger.debug("[SCHEDULER] Registered new task | task_id=%s", task.id)
    return _state_registry[key]


async def _check_reschedule_available(user_id: UUID) -> bool:
    """Return True if there are open slots remaining in today.

    MVP stub — always returns True so the reschedule option is surfaced.
    Replace with real slot-availability logic once the Scheduler agent
    exposes that endpoint.
    """
    return True


# ---------------------------------------------------------------------------
# Core polling coroutine (runs every POLL_INTERVAL_SECONDS)
# ---------------------------------------------------------------------------

async def notification_poll() -> None:
    """Single poll iteration that drives the full escalation ladder.

    Called on an interval by APScheduler.  All database mutations use
    _task_service exclusively — no direct DB access.
    """
    if _task_service is None or _db is None:
        logger.warning("[SCHEDULER] Service or DB not initialised — skipping poll.")
        return

    now = datetime.now(timezone.utc)
    logger.info("[SCHEDULER] Poll tick | utc=%s", now.isoformat())

    # ------------------------------------------------------------------ #
    # Stage 1: tasks due for PUSH (T - REMINDER_LEAD_MINUTES)             #
    # ------------------------------------------------------------------ #
    try:
        due_for_push = await _task_service.get_tasks_for_scheduling(
            _db,
            user_id=None,
            start_time=now,
            end_time=now + timedelta(minutes=REMINDER_LEAD_MINUTES),
        )
        for task in due_for_push:
            if _is_terminal(task.state):
                continue
            ns = _get_or_create_state(task)
            if ns.reminder_sent_at is None and task.state == TaskState.SCHEDULED:
                logger.info(
                    "[SCHEDULER] Stage 1 — sending PUSH | task_id=%s title=%s",
                    task.id, task.title,
                )
                ok = send_push_notification(
                    task_id=task.id,
                    task_title=task.title,
                    scheduled_at=task.start_time,
                    user_id=task.user_id,
                )
                if ok:
                    ns.reminder_sent_at = now
                    await _task_service.update_task(
                        _db,
                        task_id=task.id,
                        data=TaskUpdateDTO(reminder_sent_at=now),
                    )
    except Exception as exc:  # noqa: BLE001
        logger.error("[SCHEDULER] Stage 1 error: %s", exc)

    # ------------------------------------------------------------------ #
    # Stage 2: tasks due for WHATSAPP escalation                          #
    # (push sent, still SCHEDULED, within escalation window)              #
    # ------------------------------------------------------------------ #
    try:
        due_for_whatsapp = await _task_service.get_tasks_for_scheduling(
            _db,
            user_id=None,
            start_time=now - timedelta(minutes=ESCALATION_WINDOW),
            end_time=now,
        )
        for task in due_for_whatsapp:
            if _is_terminal(task.state):
                _state_registry.pop(str(task.id), None)
                continue
            ns = _get_or_create_state(task)
            if (
                ns.reminder_sent_at is not None
                and ns.whatsapp_sent_at is None
                and task.state == TaskState.SCHEDULED
            ):
                logger.info(
                    "[SCHEDULER] Stage 2 — sending WHATSAPP | task_id=%s title=%s",
                    task.id, task.title,
                )
                reschedule_ok = await _check_reschedule_available(task.user_id)
                user_phone = os.getenv("DEFAULT_USER_PHONE", "+10000000000")
                ok = send_whatsapp_notification(
                    task_id=task.id,
                    task_title=task.title,
                    scheduled_at=task.start_time,
                    user_phone=user_phone,
                    reschedule_available=reschedule_ok,
                )
                if ok:
                    ns.whatsapp_sent_at = now
                    await _task_service.update_task(
                        _db,
                        task_id=task.id,
                        data=TaskUpdateDTO(whatsapp_sent_at=now),
                    )
    except Exception as exc:  # noqa: BLE001
        logger.error("[SCHEDULER] Stage 2 error: %s", exc)

    # ------------------------------------------------------------------ #
    # Stage 3: tasks due for PHONE CALL escalation                        #
    # ------------------------------------------------------------------ #
    try:
        due_for_call = await _task_service.get_tasks_for_scheduling(
            _db,
            user_id=None,
            start_time=now - timedelta(minutes=ESCALATION_WINDOW * 2),
            end_time=now - timedelta(minutes=ESCALATION_WINDOW),
        )
        for task in due_for_call:
            if _is_terminal(task.state):
                _state_registry.pop(str(task.id), None)
                continue
            ns = _get_or_create_state(task)
            if (
                ns.whatsapp_sent_at is not None
                and ns.call_sent_at is None
                and task.state == TaskState.SCHEDULED
            ):
                logger.info(
                    "[SCHEDULER] Stage 3 — initiating CALL | task_id=%s title=%s",
                    task.id, task.title,
                )
                user_phone = os.getenv("DEFAULT_USER_PHONE", "+10000000000")
                call_sid = send_phone_call(
                    task_id=task.id,
                    task_title=task.title,
                    scheduled_at=task.start_time,
                    user_phone=user_phone,
                    webhook_base_url=WEBHOOK_BASE_URL,
                )
                if call_sid:
                    ns.call_sent_at = now
                    await _task_service.update_task(
                        _db,
                        task_id=task.id,
                        data=TaskUpdateDTO(call_sent_at=now),
                    )
    except Exception as exc:  # noqa: BLE001
        logger.error("[SCHEDULER] Stage 3 error: %s", exc)

    # ------------------------------------------------------------------ #
    # Stage 4: auto-mark MISSED + notify Pattern Observer                 #
    # ------------------------------------------------------------------ #
    try:
        overdue = await _task_service.get_tasks_for_scheduling(
            _db,
            user_id=None,
            start_time=now - timedelta(minutes=ESCALATION_WINDOW * 3),
            end_time=now - timedelta(minutes=ESCALATION_WINDOW * 2),
        )
        to_auto_miss = []
        for task in overdue:
            ns = _get_or_create_state(task)
            if ns.call_sent_at is not None and task.state == TaskState.SCHEDULED:
                to_auto_miss.append(task)

        if to_auto_miss:
            task_ids = [t.id for t in to_auto_miss]
            updated = await _task_service.bulk_update_state(
                _db,
                task_ids=task_ids,
                new_state=TaskState.MISSED,
            )
            logger.warning(
                "[SCHEDULER] Stage 4 — auto-missed %d task(s)", updated
            )
            for task in to_auto_miss:
                ns = _get_or_create_state(task)
                ns.missed_at = now
                ns.consecutive_miss_count += 1
                if ns.consecutive_miss_count >= CONSECUTIVE_MISS_THRESHOLD:
                    notify_pattern_observer(
                        task_id=task.id,
                        user_id=task.user_id,
                        consecutive_miss_count=ns.consecutive_miss_count,
                    )
                _state_registry.pop(str(task.id), None)
    except Exception as exc:  # noqa: BLE001
        logger.error("[SCHEDULER] Stage 4 error: %s", exc)


# ---------------------------------------------------------------------------
# Lifecycle helpers called from main.py startup / shutdown hooks
# ---------------------------------------------------------------------------

def start_scheduler(task_service: DaoTaskService, db: DatabaseSession) -> AsyncIOScheduler:
    """Create, configure, and start the background APScheduler.

    Args:
        task_service: Initialised DaoTaskService instance.
        db: Active database session passed from the FastAPI app.

    Returns:
        The running AsyncIOScheduler instance.
    """
    global _task_service, _db, _scheduler  # noqa: PLW0603
    _task_service = task_service
    _db = db

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        notification_poll,
        trigger=IntervalTrigger(seconds=POLL_INTERVAL_SECONDS),
        id="notification_poll",
        name="Notifier Agent — escalation poll",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "[SCHEDULER] Started | interval=%ds lead=%dm window=%dm",
        POLL_INTERVAL_SECONDS, REMINDER_LEAD_MINUTES, ESCALATION_WINDOW,
    )
    return scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler on application teardown."""
    global _scheduler  # noqa: PLW0603
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Stopped.")
    _scheduler = None

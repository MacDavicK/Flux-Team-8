"""
15.1 — Notifier worker entry point.

Runs the APScheduler poll loop with a SQLAlchemyJobStore backed by Postgres.
"""
from __future__ import annotations

import asyncio
import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.supabase import close_pool, init_pool
from notifier.poll import notification_poll
from notifier.recovery import recover_stuck_dispatches

logger = logging.getLogger(__name__)


def _sqlalchemy_url() -> str:
    """15.1.1 — Strip +asyncpg for sync SQLAlchemy URL."""
    return (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
    )


async def main() -> None:
    await init_pool()

    # 15.1.2 — Recover stuck dispatches before starting scheduler
    await recover_stuck_dispatches()

    jobstores = {"default": SQLAlchemyJobStore(url=_sqlalchemy_url())}
    scheduler = AsyncIOScheduler(jobstores=jobstores)

    # 15.1.3 — Poll job with interval trigger
    scheduler.add_job(
        notification_poll,
        trigger="interval",
        seconds=settings.notification_poll_interval_seconds,
        id="notification_poll",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        "Notifier scheduler started (poll interval: %ds)",
        settings.notification_poll_interval_seconds,
    )

    try:
        # 15.1.4 — Keep-alive
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        await close_pool()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

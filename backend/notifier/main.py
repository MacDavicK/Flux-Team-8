"""
15.1 — Notifier worker entry point.

Runs a simple asyncio poll loop — no APScheduler dependency needed.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.services.supabase import close_pool, init_pool
from notifier.poll import notification_poll
from notifier.recovery import recover_stuck_dispatches

logger = logging.getLogger(__name__)


async def main() -> None:
    await init_pool()

    # 15.1.2 — Recover stuck dispatches before starting poll loop
    await recover_stuck_dispatches()

    logger.info(
        "Notifier poll loop started (interval: %ds) at %s",
        settings.notification_poll_interval_seconds,
        datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    )

    while True:
        try:
            await notification_poll()
        except Exception as exc:
            logger.exception("notification_poll unhandled error: %s", exc)
        await asyncio.sleep(settings.notification_poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    finally:
        asyncio.run(close_pool())

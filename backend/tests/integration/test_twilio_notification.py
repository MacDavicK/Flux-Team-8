"""
Integration test for Twilio WhatsApp notification flow.

Sends a real WhatsApp message and simulates the webhook to verify:
1. Message is sent via Twilio
2. Webhook receives and processes user reply correctly

Run from backend/ (API must be running on localhost:8000):
  uv sync --extra dev
  uv run pytest tests/integration/test_twilio_notification.py -v -s

Requires: DB with a user (phone_verified, whatsapp_opt_in_at, notification_preferences.phone_number)
          and a task eligible for WhatsApp escalation. Creates a test task if none exists.

Note: When running from host (not Docker), host.docker.internal may not resolve. Use
  DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
  SUPABASE_URL=http://127.0.0.1:54321/
  or set MIGRATION_DATABASE_URL (tests will prefer it for DB when running).
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
import pytest
from twilio.request_validator import RequestValidator

# conftest.py sets DATABASE_URL/SUPABASE_URL to 127.0.0.1 when running from host

# Configure verbose logging for this test
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Skip if no DB/Twilio (e.g. in CI without credentials)
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_TWILIO_INTEGRATION") == "1",
    reason="SKIP_TWILIO_INTEGRATION=1",
)


def _compute_twilio_signature(url: str, params: dict[str, str], auth_token: str) -> str:
    """Compute X-Twilio-Signature for webhook request."""
    validator = RequestValidator(auth_token)
    return validator.compute_signature(url, params)


async def _get_eligible_task_and_user(db):
    """Find a user+task eligible for WhatsApp. Returns row or None."""
    return await db.fetchrow(
        """
        SELECT t.id, t.user_id, t.title, u.phone_verified, u.whatsapp_opt_in_at,
               u.notification_preferences->>'phone_number' AS phone
        FROM tasks t
        JOIN users u ON u.id = t.user_id
        WHERE t.status = 'pending'
          AND t.escalation_policy IN ('standard', 'aggressive')
          AND t.reminder_sent_at IS NOT NULL
          AND t.whatsapp_sent_at IS NULL
          AND u.phone_verified = true
          AND u.whatsapp_opt_in_at IS NOT NULL
          AND u.notification_preferences->>'phone_number' IS NOT NULL
        LIMIT 1
        """
    )


async def _create_test_task_if_needed(db):
    """Create a minimal test task if none exists. Returns task_id or None."""
    try:
        # Find any user with phone setup
        user = await db.fetchrow(
            """
            SELECT id FROM users
            WHERE phone_verified = true
              AND whatsapp_opt_in_at IS NOT NULL
              AND notification_preferences->>'phone_number' IS NOT NULL
            LIMIT 1
            """
        )
        if not user:
            logger.warning("No user with phone_verified + whatsapp_opt_in found. Skipping.")
            return None

        # Create a task eligible for WhatsApp
        task_id = await db.fetchval(
            """
            INSERT INTO tasks (user_id, title, status, scheduled_at, trigger_type,
                              escalation_policy, reminder_sent_at)
            VALUES ($1, 'Test notification task', 'pending', now() - interval '5 minutes',
                    'time', 'standard', now() - interval '15 minutes')
            RETURNING id
            """,
            user["id"],
        )
        logger.info("Created test task: %s for user %s", task_id, user["id"])
        return str(task_id)
    except Exception as e:
        logger.warning("Could not create test task: %s", e)
        return None


@pytest.mark.asyncio
async def test_twilio_whatsapp_send_and_webhook():
    """
    Send a WhatsApp notification and simulate the webhook.
    Logs every step so you can see what's happening.
    """
    from app.config import settings
    from app.services.supabase import close_pool, init_pool
    from app.services.twilio_service import dispatch_whatsapp

    await init_pool()
    from app.services.supabase import db

    try:
        # 1. Ensure we have an eligible task
        row = await _get_eligible_task_and_user(db)
        if not row:
            task_id = await _create_test_task_if_needed(db)
            if not task_id:
                pytest.skip("No eligible user/task for WhatsApp. Set up a user with phone + whatsapp_opt_in.")
            row = await _get_eligible_task_and_user(db)
            if not row:
                pytest.skip("Still no eligible task after create attempt.")

        task = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "title": row["title"] or "Test Task",
        }
        phone = row["phone"]

        logger.info("=== Step 1: Sending WhatsApp ===")
        logger.info("Task: %s", task)
        logger.info("User phone: %s", phone)

        # 2. Send WhatsApp
        message_sid = await dispatch_whatsapp(task)
        logger.info("WhatsApp sent! MessageSid=%s", message_sid)

        # 3. Insert notification_log so webhook can find the task (simulates notifier)
        # Webhook fallback looks up by user + most recent pending; we need a row with response=NULL
        try:
            await db.execute(
                "INSERT INTO notification_log (task_id, channel, external_id) VALUES ($1, 'whatsapp', $2)",
                task["id"],
                message_sid,
            )
        except Exception as e:
            if "unique" not in str(e).lower() and "duplicate" not in str(e).lower():
                raise
            logger.info("notification_log already exists for task_id=%s", task["id"])
        else:
            logger.info("notification_log inserted for task_id=%s external_id=%s", task["id"], message_sid)

        # 4. Simulate webhook: user replies "1" (done)
        # Use localhost so we hit the running API; signature must match the exact URL
        webhook_url = "http://localhost:8000/api/v1/webhooks/twilio/whatsapp"

        # Twilio sends the INCOMING message's MessageSid (different from our outbound)
        incoming_message_sid = f"SM{message_sid[-12:]}" if len(message_sid) > 12 else f"SM{message_sid}"

        params: dict[str, str] = {
            "MessageSid": incoming_message_sid,
            "From": f"whatsapp:{phone}",
            "WaId": phone,
            "Body": "1",
        }
        signature = _compute_twilio_signature(webhook_url, params, settings.twilio_auth_token)

        logger.info("=== Step 2: Simulating webhook ===")
        logger.info("Webhook URL: %s", webhook_url)
        logger.info("Params: %s", params)
        logger.info("Signature: %s...", signature[:20] if signature else "N/A")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                data=params,
                headers={"X-Twilio-Signature": signature},
            )

        logger.info("Webhook response: status=%s body=%s", resp.status_code, resp.text[:200])

        assert resp.status_code == 200, f"Webhook failed: {resp.status_code} {resp.text}"

        # 5. Verify task was updated
        task_row = await db.fetchrow(
            "SELECT status, completed_at FROM tasks WHERE id = $1", task["id"]
        )
        log_row = await db.fetchrow(
            "SELECT response, responded_at FROM notification_log WHERE task_id = $1 AND channel = 'whatsapp'",
            task["id"],
        )

        logger.info("=== Step 3: Verification ===")
        logger.info("Task: status=%s completed_at=%s", task_row["status"], task_row["completed_at"])
        logger.info("notification_log: response=%s responded_at=%s", log_row["response"], log_row["responded_at"])

        assert task_row["status"] == "done"
        assert task_row["completed_at"] is not None
        assert log_row["response"] == "done"
        assert log_row["responded_at"] is not None

        logger.info("=== Test PASSED ===")

    finally:
        await close_pool()


async def _main():
    """Run the test manually for debugging."""
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    await test_twilio_whatsapp_send_and_webhook()


if __name__ == "__main__":
    asyncio.run(_main())

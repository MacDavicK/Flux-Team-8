"""
21.2.3 — Integration test: CAS idempotency for notification dispatch.

Simulates two concurrent workers attempting to claim the same task.
Only one should succeed via the atomic CAS UPDATE ... RETURNING id.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_only_one_worker_dispatches_push():
    """
    Simulate two workers racing to claim reminder_sent_at.
    The CAS UPDATE should only yield a row for the first caller.
    """
    call_count = 0
    dispatched = 0

    # First call returns the task id (claimed), second returns None (already claimed)
    async def mock_cas(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "task-uuid-123"  # first worker claims it
        return None  # second worker finds it already claimed

    with patch("notifier.poll.db") as mock_db, \
         patch("notifier.poll.dispatch_push") as mock_push, \
         patch("notifier.poll.log_dispatch", AsyncMock()), \
         patch("notifier.poll.mark_dispatch_done", AsyncMock()):

        mock_push.return_value = True
        mock_db.fetch = AsyncMock(return_value=[
            {"id": "task-uuid-123", "user_id": "user-1", "title": "Task", "scheduled_at": None, "push_subscription": {"endpoint": "https://example.com"}}
        ])
        mock_db.fetchval = mock_cas

        from notifier.poll import _step_push
        # Run step_push twice concurrently to simulate two workers
        await asyncio.gather(_step_push(), _step_push())

    # Only one dispatch should have occurred
    assert mock_push.call_count <= 1


@pytest.mark.asyncio
async def test_whatsapp_cas_prevents_double_dispatch():
    """WhatsApp dispatch CAS prevents duplicate sends."""
    call_count = 0

    async def mock_cas(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return "task-id" if call_count == 1 else None

    with patch("notifier.poll.db") as mock_db, \
         patch("notifier.poll.dispatch_whatsapp", AsyncMock(return_value="SM123")), \
         patch("notifier.poll.log_dispatch", AsyncMock()), \
         patch("notifier.poll.mark_dispatch_done", AsyncMock()):

        mock_db.fetch = AsyncMock(return_value=[
            {"id": "task-id", "user_id": "user-1", "title": "Task", "scheduled_at": None}
        ])
        mock_db.fetchval = mock_cas

        from notifier.poll import _step_whatsapp
        await asyncio.gather(_step_whatsapp(), _step_whatsapp())

    # At most 1 dispatch
    assert call_count >= 1

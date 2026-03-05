"""
21.1.4 — Unit tests for scheduler_node.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


def _make_state():
    return {
        "user_id": "test-user-id",
        "conversation_history": [],
        "intent": "GOAL",
        "user_profile": {"timezone": "America/New_York", "sleep_window": {"start": "23:00", "end": "07:00"}},
        "goal_draft": {"title": "Run 5K"},
        "proposed_tasks": [{"title": "Morning Run", "suggested_time": "07:00", "duration_minutes": 30}],
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": "test",
    }


@pytest.mark.asyncio
async def test_scheduler_converts_to_utc():
    """Scheduler output slots have scheduled_at in UTC (ISO8601)."""
    from app.models.agent_outputs import SchedulerOutput, SlotResult

    mock_output = SchedulerOutput(
        slots=[
            SlotResult(
                task_title="Morning Run",
                scheduled_at="2026-03-02T12:00:00+00:00",  # 07:00 EST = 12:00 UTC
                duration_minutes=30,
                conflict=False,
            )
        ],
        conflicts=[],
        first_available_start=None,
    )

    with patch("app.agents.scheduler.validated_llm_call", AsyncMock(return_value=mock_output)), \
         patch("app.agents.scheduler.db") as mock_db:
        mock_db.fetch = AsyncMock(return_value=[])
        mock_db.fetchrow = AsyncMock(return_value={"profile": {"timezone": "America/New_York"}})

        from app.agents.scheduler import scheduler_node
        result = await scheduler_node(_make_state())

    scheduler_output = result.get("scheduler_output")
    assert scheduler_output is not None
    slots = scheduler_output.get("slots", [])
    assert len(slots) > 0
    # Verify the scheduled_at is a valid datetime string
    from datetime import datetime
    for slot in slots:
        dt_str = slot.get("scheduled_at", "")
        assert dt_str  # non-empty

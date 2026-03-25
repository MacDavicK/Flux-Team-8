"""
Unit tests for scheduler_node (scheduler.py).

Focused on checklist item 13:
  Scheduler projections use canonical_scheduled_at as the RRULE anchor
  when available, rather than scheduled_at.

This ensures that after a single-occurrence reschedule, future busy-slot
projections still reflect the true series position (e.g. 9 AM) rather than
the rescheduled time (e.g. 8 AM), giving correct availability windows.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pendulum
import pytest


@pytest.mark.asyncio
async def test_scheduler_uses_canonical_scheduled_at_as_projection_anchor():
    """
    When canonical_scheduled_at differs from scheduled_at (task was
    single-occurrence rescheduled), projected_occurrences_in_window must
    receive canonical_scheduled_at as the anchor — not scheduled_at.
    """
    canonical = pendulum.datetime(2026, 3, 23, 9, 0, tz="America/New_York").in_timezone(
        "UTC"
    )
    rescheduled = pendulum.datetime(
        2026, 3, 23, 8, 0, tz="America/New_York"
    ).in_timezone("UTC")  # pulled back to 08:00

    recurring_row = {
        "title": "Morning run",
        "scheduled_at": rescheduled,
        "canonical_scheduled_at": canonical,
        "duration_minutes": 30,
        "recurrence_rule": "FREQ=DAILY",
    }

    state = {
        "user_id": "user-uuid-1111",
        "user_profile": {"timezone": "America/New_York"},
        "goal_draft": {"plan": {"proposed_tasks": []}},
        "goal_start_date": None,
        "pattern_output": {},
    }

    from app.models.agent_outputs import SchedulerOutput

    captured_anchors: list[pendulum.DateTime] = []

    def _fake_projected(rrule, anchor, window_start, window_end, tz):
        captured_anchors.append(anchor)
        return []

    with (
        patch("app.agents.scheduler.db") as mock_db,
        patch(
            "app.agents.scheduler.projected_occurrences_in_window",
            side_effect=_fake_projected,
        ),
        patch(
            "app.agents.scheduler.validated_llm_call",
            new=AsyncMock(return_value=SchedulerOutput(slots=[], conflicts=[])),
        ),
    ):
        mock_db.fetch = AsyncMock(
            side_effect=[
                [],  # existing_rows (materialized tasks in window)
                [recurring_row],  # recurring_rows (RRULE projection source)
            ]
        )

        from app.agents.scheduler import scheduler_node

        await scheduler_node(state)

    assert len(captured_anchors) == 1, (
        "projected_occurrences_in_window should be called once"
    )

    # Anchor must be the canonical time (09:00 NY), not the rescheduled time (08:00 NY).
    expected_anchor = pendulum.instance(canonical)
    assert captured_anchors[0] == expected_anchor, (
        f"Expected anchor={expected_anchor.isoformat()!r} (canonical), "
        f"got {captured_anchors[0].isoformat()!r} (rescheduled)"
    )

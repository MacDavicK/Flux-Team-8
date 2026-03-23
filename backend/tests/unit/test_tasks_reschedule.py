"""
Unit tests for reschedule_confirm (tasks.py).

Focused on checklist item 12:
  Goal-linked task: canonical_scheduled_at survives the goal-linked
  single-reschedule INSERT so advance_recurring_task continues the series
  from the correct canonical position.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

UTC = timezone.utc

# Stub out modules that require psycopg/libpq (not available in unit test env).
# Must be set before app.api.v1.tasks is imported.
sys.modules.setdefault("app.agents.graph", MagicMock(compiled_graph=MagicMock()))


@pytest.mark.asyncio
async def test_goal_linked_single_reschedule_preserves_canonical():
    """
    Goal-linked single-occurrence reschedule: the INSERT for the new pending
    row must include canonical_scheduled_at copied from the original task.

    Without this the series anchor would be lost and advance_recurring_task
    would use the rescheduled time as the RRULE anchor on the next advance,
    causing anchor drift (Flaw 1 from the design spec).
    """
    USER_ID = "11111111-1111-1111-1111-111111111111"
    canonical_time = datetime(2026, 3, 23, 14, 0, 0, tzinfo=UTC)  # 09:00 NY

    original_task = {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "user_id": USER_ID,
        "goal_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        "title": "Morning run",
        "description": "",
        "status": "pending",
        "scheduled_at": datetime(
            2026, 3, 23, 15, 0, 0, tzinfo=UTC
        ),  # 10:00 NY (rescheduled)
        "duration_minutes": 30,
        "trigger_type": "time",
        "location_trigger": None,
        "recurrence_rule": "FREQ=DAILY",
        "escalation_policy": "standard",
        "canonical_scheduled_at": canonical_time,
    }

    new_scheduled_iso = "2026-03-23T17:00:00+00:00"  # 12:00 NY — new rescheduled time

    from app.api.v1.tasks import reschedule_confirm
    from app.models.api_schemas import RescheduleConfirmRequest

    with (
        patch(
            "app.api.v1.tasks._fetch_task_or_404",
            new=AsyncMock(return_value=original_task),
        ),
        patch("app.api.v1.tasks.db") as mock_db,
    ):
        mock_db.execute = AsyncMock()
        mock_db.fetchval = AsyncMock(
            return_value=uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        )

        body = RescheduleConfirmRequest(scheduled_at=new_scheduled_iso, scope="one")
        current_user = {"sub": USER_ID}

        result = await reschedule_confirm(
            task_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            body=body,
            current_user=current_user,
        )

    assert result["status"] == "rescheduled"

    # db.fetchval is the goal-linked INSERT (RETURNING id).
    # Positional args: SQL, user_uuid($1), goal_id($2), title($3), description($4),
    #   scheduled_at($5), duration_minutes($6), trigger_type($7),
    #   recurrence_rule($8), escalation_policy($9), canonical_scheduled_at($10)
    insert_args = mock_db.fetchval.call_args[0]
    canonical_passed = insert_args[10]
    assert canonical_passed == canonical_time, (
        f"Expected canonical_scheduled_at={canonical_time!r} in INSERT, "
        f"got {canonical_passed!r}"
    )

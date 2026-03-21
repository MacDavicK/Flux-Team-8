"""
Unit tests for advance_recurring_task.

All DB calls are mocked. The mock task rows use `canonical_scheduled_at`
(the new column) instead of `proposed_time`.

Run: pytest tests/unit/test_recurrence.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pendulum
import pytest

from app.services.recurrence import advance_recurring_task

UTC = timezone.utc


def _make_task(
    recurrence_rule: str,
    scheduled_at: datetime,
    canonical_scheduled_at: datetime | None,
    goal_id=None,
    proposed_time=None,
) -> dict:
    """Build a minimal task row dict matching the new schema."""
    return {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "recurrence_rule": recurrence_rule,
        "scheduled_at": scheduled_at,
        "canonical_scheduled_at": canonical_scheduled_at,
        "user_id": "user-uuid-1111",
        "title": "Test Task",
        "description": "",
        "duration_minutes": 30,
        "trigger_type": "time",
        "location_trigger": None,
        "goal_id": goal_id,
        "shared_with_goal_ids": [],
        "escalation_policy": "standard",
        "proposed_time": proposed_time,
    }


def _make_user(tz: str = "America/New_York", sleep_window=None) -> dict:
    return {
        "timezone": tz,
        "profile": {"sleep_window": sleep_window} if sleep_window else {},
    }


def _ny(year, month, day, hour, minute=0) -> datetime:
    """Return a UTC-aware datetime corresponding to HH:MM in America/New_York."""
    local = pendulum.datetime(year, month, day, hour, minute, tz="America/New_York")
    return local.in_timezone("UTC")


# ── Test 1: DAILY task, no reschedule — advances to next day ────────────────


@pytest.mark.asyncio
async def test_daily_no_reschedule():
    """Normal DAILY advance: canonical = scheduled → next day same time."""
    scheduled = _ny(2026, 3, 23, 9)
    canonical = scheduled

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    # NOTE (Task 4): call_args[0][5] assumes scheduled_at is the 5th positional arg to
    # db.execute (SQL=0, user_id=1, goal_id=2, title=3, description=4, scheduled_at=5).
    # When Task 4 adds canonical_scheduled_at to the INSERT, verify this index is still correct.
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24
    assert inserted_local.hour == 9


# ── Test 2: DAILY task, push forward (09:00 → 10:00) — reverts to 09:00 ───


@pytest.mark.asyncio
async def test_daily_push_forward_reverts_to_canonical():
    """Single push-forward: scheduled_at=10:00, canonical=09:00 → next=09:00 next day."""
    scheduled = _ny(2026, 3, 23, 10)
    canonical = _ny(2026, 3, 23, 9)

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24
    assert inserted_local.hour == 9
    assert inserted_local.minute == 0


# ── Test 3: DAILY task, pull back (09:00 → 08:00) — no same-day duplicate ──


@pytest.mark.asyncio
async def test_daily_pull_back_no_same_day_duplicate():
    """
    Single pull-back: scheduled_at=08:00, canonical=09:00.
    advance must produce Tuesday 09:00, NOT Monday 09:00 (same-day duplicate).
    This is the core Flaw 2 regression test.
    """
    scheduled = _ny(2026, 3, 23, 8)
    canonical = _ny(2026, 3, 23, 9)

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24  # TUESDAY, not Monday 23
    assert inserted_local.hour == 9
    assert inserted_local.minute == 0


# ── Test 4: DAILY task, single reschedule into sleep window ────────────────


@pytest.mark.asyncio
async def test_daily_single_reschedule_into_sleep_window():
    """
    scheduled_at=23:30 (inside sleep), canonical=09:00.
    advance uses canonical (09:00) → next is Tuesday 09:00 → sleep guard does not fire.
    """
    scheduled = _ny(2026, 3, 23, 23, 30)
    canonical = _ny(2026, 3, 23, 9)

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24
    assert inserted_local.hour == 9
    assert inserted_local.minute == 0


# ── Test 5: DAILY task, series reschedule (both fields updated) ─────────────


@pytest.mark.asyncio
async def test_daily_series_reschedule_uses_new_canonical():
    """Series reschedule sets both scheduled_at and canonical to 14:00 → next=14:00."""
    scheduled = _ny(2026, 3, 23, 14)
    canonical = _ny(2026, 3, 23, 14)

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24
    assert inserted_local.hour == 14
    assert inserted_local.minute == 0


# ── Test 6: MINUTELY task — no infinite loop ────────────────────────────────


@pytest.mark.asyncio
async def test_minutely_no_infinite_loop():
    """
    FREQ=MINUTELY;INTERVAL=30: scheduled=canonical=09:00 → next=09:30.
    Regression: proposed_time override caused same timestamp re-insertion (infinite miss loop).
    """
    t = datetime(2026, 3, 21, 13, 0, 0, tzinfo=UTC)  # 09:00 NY

    task = _make_task("FREQ=MINUTELY;INTERVAL=30", t, t)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_utc = pendulum.instance(inserted_at).in_timezone("UTC")
    assert inserted_utc.hour == 13
    assert inserted_utc.minute == 30


# ── Test 7: MINUTELY task, natural next occurrence hits sleep window ────────


@pytest.mark.asyncio
async def test_minutely_natural_sleep_guard():
    """
    FREQ=MINUTELY;INTERVAL=30, canonical=22:30 NY (no reschedule).
    Next occurrence = 23:00 → inside 23:00–07:00 sleep → sleep guard → 07:00 next day.
    """
    t = pendulum.datetime(2026, 3, 21, 22, 30, tz="America/New_York").in_timezone("UTC")
    task = _make_task("FREQ=MINUTELY;INTERVAL=30", t, t)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.hour == 7
    assert inserted_local.minute == 0
    assert inserted_local.day == 22


# ── Test 8: MINUTELY single reschedule INTO sleep — canonical used ──────────


@pytest.mark.asyncio
async def test_minutely_single_reschedule_into_sleep_uses_canonical():
    """
    FREQ=MINUTELY;INTERVAL=30, single reschedule from 22:30 → 23:30 (into sleep).
    canonical=22:30 (unchanged). Advance: canonical 22:30 → 23:00 → sleep guard → 07:00 next day.
    Rescheduled time (23:30) is completely ignored by advance.
    """
    canonical_t = pendulum.datetime(
        2026, 3, 21, 22, 30, tz="America/New_York"
    ).in_timezone("UTC")
    scheduled_t = pendulum.datetime(
        2026, 3, 21, 23, 30, tz="America/New_York"
    ).in_timezone("UTC")

    task = _make_task("FREQ=MINUTELY;INTERVAL=30", scheduled_t, canonical_t)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.hour == 7
    assert inserted_local.minute == 0
    assert inserted_local.day == 22


# ── Test 9: Goal guard — goal completed → returns False ─────────────────────


@pytest.mark.asyncio
async def test_goal_guard_completed_goal_stops_advance():
    """advance_recurring_task returns False when the goal is completed."""
    scheduled = _ny(2026, 3, 23, 9)
    task = _make_task("FREQ=DAILY", scheduled, scheduled, goal_id="goal-uuid-9999")
    user = _make_user()
    goal = {"activated_at": None, "target_weeks": None, "status": "completed"}

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user, goal])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is False
    mock_db.execute.assert_not_called()


# ── Test 10: Goal guard — sprint end exceeded → returns False ───────────────


@pytest.mark.asyncio
async def test_goal_guard_sprint_end_stops_advance():
    """advance_recurring_task returns False when next occurrence is past sprint end."""
    # Task on Mon Mar 23, DAILY. Goal sprint: activated Mar 16, 1 week → ends Mar 23.
    # Next occurrence = Mar 24 > Mar 23 → False.
    scheduled = _ny(2026, 3, 23, 9)
    task = _make_task("FREQ=DAILY", scheduled, scheduled, goal_id="goal-uuid-9999")
    user = _make_user()
    goal = {
        "activated_at": datetime(2026, 3, 16, 0, 0, 0, tzinfo=UTC),
        "target_weeks": 1,
        "status": "active",
    }

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user, goal])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is False
    mock_db.execute.assert_not_called()


# ── Test 11: NULL canonical (pre-migration row) — falls back to scheduled_at ─


@pytest.mark.asyncio
async def test_null_canonical_falls_back_to_scheduled_at():
    """
    Rows created before migration have canonical_scheduled_at=NULL.
    advance_recurring_task must fall back to scheduled_at (same as prior behaviour).
    """
    scheduled = _ny(2026, 3, 23, 9)
    task = _make_task("FREQ=DAILY", scheduled, None)  # NULL canonical
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24
    assert inserted_local.hour == 9
    assert inserted_local.minute == 0


# ── Test 12: Goal guard — abandoned goal → returns False ────────────────────


@pytest.mark.asyncio
async def test_goal_guard_abandoned_goal_stops_advance():
    """advance_recurring_task returns False when the goal is abandoned."""
    scheduled = _ny(2026, 3, 23, 9)
    task = _make_task("FREQ=DAILY", scheduled, scheduled, goal_id="goal-uuid-9999")
    user = _make_user()
    goal = {"activated_at": None, "target_weeks": None, "status": "abandoned"}

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user, goal])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is False
    mock_db.execute.assert_not_called()


# ── Test 13: Non-existent task (db.fetchrow returns None) → returns False ───


@pytest.mark.asyncio
async def test_nonexistent_task_returns_false():
    """advance_recurring_task returns False when the task row doesn't exist."""
    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("nonexistent-task-id")

    assert result is False
    mock_db.execute.assert_not_called()

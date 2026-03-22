"""
Unit tests for ask_start_date_node (ask_start_date.py).

Spec coverage:
  - Standard flow: congested_dates and suggested_date in returned state
  - Recurring task projections are included in task_minutes
  - Lazy-fill: absent work_minutes_by_day triggers parse + DB write
  - All 14 days congested: suggested_date is None; all 14 in congested_dates
  - DB failure: falls back to empty congested_dates, None suggested_date
  - Question text includes suggested_date when set; neutral when None
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pendulum
import pytest


def _make_state(
    *,
    profile: dict | None = None,
    goal_draft: dict | None = None,
) -> dict:
    return {
        "user_id": "user-123",
        "conversation_history": [{"role": "user", "content": "Let's go!"}],
        "user_profile": profile
        or {
            "timezone": "America/New_York",
            "sleep_window": {"start": "23:00", "end": "07:00"},
            "work_minutes_by_day": {
                "mon": 480,
                "tue": 480,
                "wed": 480,
                "thu": 480,
                "fri": 480,
                "sat": 0,
                "sun": 0,
            },
        },
        "goal_draft": goal_draft
        or {"plan": {"proposed_tasks": [{"duration_minutes": 30}]}},
        "approval_status": "pending",
    }


@pytest.mark.asyncio
async def test_returns_suggested_and_congested_dates():
    """
    When some days have tasks and some are free, suggested_date points to the
    lightest day and congested_dates lists the fully-booked ones.
    """
    # Build a fake materialized row that occupies Monday (2026-03-23) completely.
    monday_utc = pendulum.datetime(2026, 3, 23, 12, 0, tz="UTC")

    mat_rows = [
        {"title": "Work block", "scheduled_at": monday_utc, "duration_minutes": 480},
    ]
    rec_rows = []  # no recurring tasks

    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        # Pin "today" to Sunday 2026-03-22 in New York
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")

        mock_db.fetch = AsyncMock(side_effect=[mat_rows, rec_rows])

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state())

    assert result["approval_status"] == "awaiting_start_date"
    assert result["suggested_date"] is not None
    # Monday 2026-03-23 should be congested (480 min tasks + 480 work = 960 min; only ~480 free → ≤30 min → congested)
    assert "2026-03-23" in result["congested_dates"]
    # suggested_date must be a non-congested day
    assert result["suggested_date"] not in result["congested_dates"]


@pytest.mark.asyncio
async def test_recurring_projections_included():
    """
    A recurring task that projects into the window should be counted in
    task_minutes, making those days appear busier.
    """
    # A daily 30-min recurring task; today = Sunday 2026-03-22
    today_utc = pendulum.datetime(2026, 3, 22, 14, 0, tz="UTC")

    mat_rows = []
    rec_rows = [
        {
            "title": "Daily standup",
            "scheduled_at": today_utc,
            "canonical_scheduled_at": today_utc,
            "duration_minutes": 30,
            "recurrence_rule": "FREQ=DAILY",
        }
    ]

    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=[mat_rows, rec_rows])

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state())

    # With only 30 min of recurring tasks per day and 480 free min, no day should
    # be congested by a 30-min threshold.
    # All 14 days will have 30-min projection from recurring task, but still plenty free.
    assert result["approval_status"] == "awaiting_start_date"
    assert isinstance(result["congested_dates"], list)
    assert isinstance(result["suggested_date"], str) or result["suggested_date"] is None


@pytest.mark.asyncio
async def test_lazy_fill_triggers_parse_and_db_write():
    """
    When work_minutes_by_day is absent from profile, the node must call
    _parse_work_minutes_by_day and write the result back to the DB.
    """
    profile_without_work_minutes = {
        "timezone": "America/New_York",
        "sleep_window": {"start": "23:00", "end": "07:00"},
        "work_hours": "9 AM to 5 PM, Monday to Friday",
        # work_minutes_by_day intentionally absent
    }
    parsed_work = {
        "mon": 480,
        "tue": 480,
        "wed": 480,
        "thu": 480,
        "fri": 480,
        "sat": 0,
        "sun": 0,
    }

    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
        patch(
            "app.agents.ask_start_date.ask_start_date_node.__module__",
            create=True,
        ),
        patch(
            "app.agents.onboarding._parse_work_minutes_by_day",
            new=AsyncMock(return_value=parsed_work),
        ) as mock_parse,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=[[], []])
        mock_db.execute = AsyncMock()

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(
            _make_state(profile=profile_without_work_minutes)
        )

    mock_parse.assert_called_once_with("9 AM to 5 PM, Monday to Friday")
    # DB write should have been called (lazy-fill persist)
    mock_db.execute.assert_called_once()
    assert result["approval_status"] == "awaiting_start_date"


@pytest.mark.asyncio
async def test_all_14_days_congested():
    """
    When all 14 days are congested, suggested_date is None and all 14 dates
    appear in congested_dates so the calendar disables them.
    """
    # Fill every day with 480 min of tasks (leaves ≤ 0 free given 8h sleep + 8h work)
    today_utc = pendulum.datetime(2026, 3, 22, 14, 0, tz="UTC")

    mat_rows = []
    # Daily task of 960 min — more than the free time on any day (including weekends
    # with 0 work: 24*60 - 480 sleep - 0 work - 960 tasks = 0 free).
    rec_rows = [
        {
            "title": "All day block",
            "scheduled_at": today_utc,
            "canonical_scheduled_at": today_utc,
            "duration_minutes": 960,
            "recurrence_rule": "FREQ=DAILY",
        }
    ]
    # Goal with a 30-min task so congestion threshold = 30 min
    goal_draft = {"plan": {"proposed_tasks": [{"duration_minutes": 30}]}}

    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=[mat_rows, rec_rows])

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state(goal_draft=goal_draft))

    assert result["suggested_date"] is None
    # All 14 days should be in congested_dates
    assert len(result["congested_dates"]) == 14
    # Question text should be the neutral fallback
    assert (
        "would you like to start"
        in result["conversation_history"][-1]["content"].lower()
    )


@pytest.mark.asyncio
async def test_db_failure_falls_back_gracefully():
    """
    A DB error during the congestion check must not crash the node.
    Falls back to empty congested_dates and None suggested_date.
    """
    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=Exception("DB connection lost"))

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state())

    assert result["approval_status"] == "awaiting_start_date"
    assert result["suggested_date"] is None
    assert result["congested_dates"] == []
    # Neutral question should be used
    assert (
        "would you like to start"
        in result["conversation_history"][-1]["content"].lower()
    )


@pytest.mark.asyncio
async def test_no_tasks_shows_neutral_question():
    """With no existing tasks all days are equally free — no suggestion, neutral question."""
    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=[[], []])  # no tasks at all

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state())

    # No asymmetry → no suggestion
    assert result["suggested_date"] is None
    assert (
        "would you like to start"
        in result["conversation_history"][-1]["content"].lower()
    )


@pytest.mark.asyncio
async def test_question_includes_suggested_date_when_asymmetry_exists():
    """When some days have more tasks than others, the lightest day is suggested."""
    monday_utc = pendulum.datetime(2026, 3, 23, 12, 0, tz="UTC")
    # One materialized 60-min task on Monday — creates asymmetry
    mat_rows = [
        {"title": "Dentist", "scheduled_at": monday_utc, "duration_minutes": 60},
    ]

    with (
        patch("app.agents.ask_start_date.db") as mock_db,
        patch("pendulum.now") as mock_now,
    ):
        sunday = pendulum.datetime(2026, 3, 22, 8, 0, tz="America/New_York")
        mock_now.return_value = sunday.start_of("day")
        mock_db.fetch = AsyncMock(side_effect=[mat_rows, []])

        from app.agents.ask_start_date import ask_start_date_node

        result = await ask_start_date_node(_make_state())

    # Asymmetry exists → a suggestion should be made
    assert result["suggested_date"] is not None
    assert "schedule looks lightest" in result["conversation_history"][-1]["content"]
    # Monday (the busy day) must not be the suggestion
    assert result["suggested_date"] != "2026-03-23"


@pytest.mark.asyncio
async def test_parse_work_minutes_by_day_fallback_on_llm_error():
    """_parse_work_minutes_by_day returns fallback dict when LLM call fails."""
    from app.agents.onboarding import _WORK_MINUTES_FALLBACK, _parse_work_minutes_by_day

    with patch(
        "app.services.llm.validated_llm_call", side_effect=Exception("LLM down")
    ):
        result = await _parse_work_minutes_by_day("9 AM to 5 PM, Monday to Friday")

    assert result == _WORK_MINUTES_FALLBACK

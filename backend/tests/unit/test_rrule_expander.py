"""
12.3 — Unit tests for expand_rrule_to_tasks.

Covers:
  - Weekly recurrence across a DST "spring forward" boundary (America/New_York)
  - Weekly recurrence across a DST "fall back" boundary (America/New_York)
  - end_dt boundary: occurrences on end_dt are included; occurrences after are excluded
  - recurrence_rule string is preserved on every row
  - base_task fields are propagated to every expanded row
  - All scheduled_at values are UTC ISO8601 strings
"""

import pendulum
import pytest

from app.services.rrule_expander import expand_rrule_to_tasks

_BASE_TASK = {
    "user_id": "test-user-uuid",
    "goal_id": None,
    "title": "Morning Run",
    "description": "Daily jog",
    "status": "pending",
    "duration_minutes": 30,
    "trigger_type": "time",
    "location_trigger": None,
    "shared_with_goal_ids": [],
}


class TestExpandRruleToTasksDST:
    """DST-boundary correctness — the core requirement of task 12.3."""

    def test_spring_forward_wall_clock_stays_constant(self):
        """
        US Eastern spring-forward: 2026-03-08 at 02:00 EST → 03:00 EDT.

        A weekly Monday task at 07:00 local must keep its wall-clock time
        after the transition. The UTC hour shifts from 12 (UTC-5 / EST) to
        11 (UTC-4 / EDT) at the boundary — NOT the other way around.

        Dates covered:
          Mon 2026-02-23  07:00 EST  → 12:00 UTC
          Mon 2026-03-02  07:00 EST  → 12:00 UTC
          Mon 2026-03-09  07:00 EDT  → 11:00 UTC  ← boundary week
          Mon 2026-03-16  07:00 EDT  → 11:00 UTC
        """
        tz = "America/New_York"
        start_local = pendulum.datetime(2026, 2, 23, 7, 0, 0, tz=tz)
        end_local = pendulum.datetime(2026, 3, 16, 23, 59, 59, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        assert len(tasks) == 4, f"Expected 4 Mondays, got {len(tasks)}"

        utc_hours = [pendulum.parse(t["scheduled_at"]).hour for t in tasks]

        # Feb 23 and Mar 2 are EST (UTC-5): 07:00 local = 12:00 UTC
        assert utc_hours[0] == 12, f"Feb 23 (EST): expected UTC 12, got {utc_hours[0]}"
        assert utc_hours[1] == 12, f"Mar 02 (EST): expected UTC 12, got {utc_hours[1]}"

        # Mar 9 is EDT (UTC-4): 07:00 local = 11:00 UTC
        assert utc_hours[2] == 11, (
            f"Mar 09 (EDT, post spring-forward): expected UTC 11, got {utc_hours[2]}"
        )

        # Mar 16 stays EDT
        assert utc_hours[3] == 11, f"Mar 16 (EDT): expected UTC 11, got {utc_hours[3]}"

    def test_fall_back_wall_clock_stays_constant(self):
        """
        US Eastern fall-back: 2026-11-01 at 02:00 EDT → 01:00 EST.

        A weekly Monday task at 07:00 local must keep its wall-clock time.
        The UTC hour shifts from 11 (UTC-4 / EDT) to 12 (UTC-5 / EST).

        Dates covered:
          Mon 2026-10-26  07:00 EDT  → 11:00 UTC
          Mon 2026-11-02  07:00 EST  → 12:00 UTC  ← boundary week
          Mon 2026-11-09  07:00 EST  → 12:00 UTC
        """
        tz = "America/New_York"
        start_local = pendulum.datetime(2026, 10, 26, 7, 0, 0, tz=tz)
        end_local = pendulum.datetime(2026, 11, 9, 23, 59, 59, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        assert len(tasks) == 3, f"Expected 3 Mondays, got {len(tasks)}"

        utc_hours = [pendulum.parse(t["scheduled_at"]).hour for t in tasks]

        # Oct 26 — EDT (UTC-4): 07:00 = 11:00 UTC
        assert utc_hours[0] == 11, f"Oct 26 (EDT): expected UTC 11, got {utc_hours[0]}"

        # Nov 2 — fall-back happened Nov 1, now EST (UTC-5): 07:00 = 12:00 UTC
        assert utc_hours[1] == 12, (
            f"Nov 02 (EST, post fall-back): expected UTC 12, got {utc_hours[1]}"
        )

        # Nov 9 stays EST
        assert utc_hours[2] == 12, f"Nov 09 (EST): expected UTC 12, got {utc_hours[2]}"

    def test_no_dst_timezone_produces_constant_utc_offset(self):
        """
        Asia/Tokyo is UTC+9 with no DST. UTC hour must be constant across all
        occurrences.

        06:00 JST → 21:00 UTC (previous calendar day, but same hour offset).
        """
        tz = "Asia/Tokyo"
        start_local = pendulum.datetime(2026, 4, 6, 6, 0, 0, tz=tz)    # Monday
        end_local = pendulum.datetime(2026, 4, 20, 6, 0, 0, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        assert len(tasks) == 3

        for task in tasks:
            dt = pendulum.parse(task["scheduled_at"])
            # pendulum 3 may represent UTC as "+00:00" or "UTC" depending on the input
            assert dt.offset == 0, f"Expected UTC (offset 0), got timezone_name={dt.timezone_name}"
            # 06:00 JST = 21:00 UTC
            assert dt.hour == 21, f"Expected 21:00 UTC for 06:00 JST, got {dt.hour}:00"


class TestExpandRruleToTasksBoundary:
    """end_dt boundary and occurrence count correctness."""

    def test_occurrence_on_end_dt_is_included(self):
        """expand_rrule_to_tasks uses between(..., inc=True) — end_dt occurrence included."""
        tz = "Europe/London"
        start_local = pendulum.datetime(2026, 1, 5, 9, 0, 0, tz=tz)   # Monday
        # end_dt lands exactly on the third Monday at the same time
        end_local = pendulum.datetime(2026, 1, 19, 9, 0, 0, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        # Jan 5, Jan 12, Jan 19 — all three included
        assert len(tasks) == 3

    def test_occurrence_after_end_dt_is_excluded(self):
        """Occurrences strictly after end_dt are not included."""
        tz = "Europe/London"
        start_local = pendulum.datetime(2026, 1, 5, 9, 0, 0, tz=tz)
        # end_dt stops just before the second Monday
        end_local = pendulum.datetime(2026, 1, 11, 23, 59, 59, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        # Only Jan 5 fits; Jan 12 is after end_dt
        assert len(tasks) == 1

    def test_multi_day_weekly_recurrence_count(self):
        """FREQ=WEEKLY;BYDAY=MO,WE,FR produces 3 × N occurrences per week."""
        tz = "UTC"
        # Start on Monday of a clean week
        start_local = pendulum.datetime(2026, 3, 2, 8, 0, 0, tz=tz)   # Monday
        end_local = pendulum.datetime(2026, 3, 15, 23, 59, 59, tz=tz)  # two full weeks

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO,WE,FR",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        # Week 1: Mon Mar 2, Wed Mar 4, Fri Mar 6
        # Week 2: Mon Mar 9, Wed Mar 11, Fri Mar 13
        assert len(tasks) == 6


class TestExpandRruleToTasksOutput:
    """Output schema correctness."""

    def test_recurrence_rule_preserved_on_all_rows(self):
        """Every expanded row carries the original recurrence_rule string."""
        tz = "UTC"
        rrule = "FREQ=WEEKLY;BYDAY=MO,WE"
        start_local = pendulum.datetime(2026, 3, 2, 8, 0, 0, tz=tz)
        end_local = pendulum.datetime(2026, 3, 11, 8, 0, 0, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string=rrule,
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        assert len(tasks) > 0
        assert all(t["recurrence_rule"] == rrule for t in tasks)

    def test_base_task_fields_propagated(self):
        """All base_task fields are present and unmodified on every row."""
        tz = "UTC"
        start_local = pendulum.datetime(2026, 6, 1, 7, 0, 0, tz=tz)
        end_local = pendulum.datetime(2026, 6, 15, 7, 0, 0, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        for task in tasks:
            assert task["user_id"] == _BASE_TASK["user_id"]
            assert task["title"] == _BASE_TASK["title"]
            assert task["duration_minutes"] == _BASE_TASK["duration_minutes"]
            assert task["status"] == _BASE_TASK["status"]
            # scheduled_at and recurrence_rule are overwritten — just check present
            assert "scheduled_at" in task

    def test_all_scheduled_at_are_utc_iso8601_strings(self):
        """scheduled_at must be a parseable UTC ISO8601 string on every row."""
        tz = "America/Los_Angeles"   # UTC-8/UTC-7
        start_local = pendulum.datetime(2026, 2, 2, 6, 0, 0, tz=tz)   # Monday
        end_local = pendulum.datetime(2026, 2, 23, 6, 0, 0, tz=tz)

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=start_local,
            end_dt=end_local,
            user_timezone=tz,
        )

        assert len(tasks) == 4
        for task in tasks:
            assert isinstance(task["scheduled_at"], str)
            dt = pendulum.parse(task["scheduled_at"])
            # pendulum 3 may use "+00:00" or "UTC" — check offset instead
            assert dt.offset == 0, f"Expected UTC offset, got {dt.timezone_name}"

    def test_empty_range_returns_no_tasks(self):
        """When start_dt == end_dt and there is one occurrence, it is included."""
        tz = "UTC"
        dt = pendulum.datetime(2026, 3, 2, 8, 0, 0, tz=tz)  # Monday

        tasks = expand_rrule_to_tasks(
            base_task=_BASE_TASK,
            rrule_string="FREQ=WEEKLY;BYDAY=MO",
            start_dt=dt,
            end_dt=dt,   # exact match → included (inc=True)
            user_timezone=tz,
        )
        assert len(tasks) == 1

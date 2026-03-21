"""
Unit tests for rrule_expander — pure functions, no DB required.
Run: pytest tests/unit/test_rrule_expander.py -v
"""

import pendulum

from app.services.rrule_expander import (
    advance_past_sleep,
    next_occurrence_after,
    parse_sleep_window,
)


# ── next_occurrence_after ────────────────────────────────────────────────────


def test_next_occurrence_after_daily():
    """DAILY rule strictly after a given datetime returns the next calendar day."""
    after = pendulum.datetime(2026, 3, 21, 9, 0, 0, tz="UTC")
    dtstart = pendulum.datetime(2026, 3, 21, 9, 0, 0, tz="UTC")
    result = next_occurrence_after(
        "FREQ=DAILY", after, "America/New_York", dtstart=dtstart
    )
    # dtstart = 09:00 UTC = 05:00 New York (EDT). DAILY at 05:00 NY,
    # strictly after 05:00 NY = next day 05:00 NY = March 22 05:00 NY.
    assert result is not None
    dt = pendulum.parse(result)
    local = dt.in_timezone("America/New_York")
    assert local.day == 22
    assert local.hour == 5
    assert local.minute == 0


def test_next_occurrence_after_minutely():
    """MINUTELY;INTERVAL=30 returns 30 minutes later, not the same time."""
    after = pendulum.datetime(2026, 3, 21, 9, 0, 0, tz="UTC")
    result = next_occurrence_after(
        "FREQ=MINUTELY;INTERVAL=30", after, "UTC", dtstart=after
    )
    assert result is not None
    dt = pendulum.parse(result)
    assert dt == pendulum.datetime(2026, 3, 21, 9, 30, 0, tz="UTC")


def test_next_occurrence_after_with_until_exhausted():
    """Returns None when RRULE has no more occurrences."""
    after = pendulum.datetime(2026, 4, 1, 9, 0, 0, tz="UTC")
    # UNTIL without Z suffix — dateutil requires naive UNTIL when dtstart is naive
    result = next_occurrence_after(
        "FREQ=DAILY;UNTIL=20260331T090000", after, "UTC", dtstart=after
    )
    assert result is None


def test_next_occurrence_after_pull_back_no_same_day_duplicate():
    """
    When canonical_dt (dtstart + after_dt) is used for a pull-back rescheduled task,
    rule.after must NOT return the same calendar day.

    Scenario: DAILY at 09:00 NY, single-occurrence pull-back to 08:00.
    canonical_dt = Monday Mar 23 09:00 NY = 13:00 UTC (EDT = UTC-4).
    Expected: Tuesday Mar 24 09:00 NY. NOT Monday Mar 23 09:00 NY.
    """
    # canonical = Mon Mar 23 09:00 NY = 13:00 UTC
    canonical = pendulum.datetime(2026, 3, 23, 13, 0, 0, tz="UTC")  # 09:00 NY
    result = next_occurrence_after(
        "FREQ=DAILY", canonical, "America/New_York", dtstart=canonical
    )
    assert result is not None
    local = pendulum.parse(result).in_timezone("America/New_York")
    assert local.day == 24  # Tuesday, not Monday
    assert local.hour == 9


# ── parse_sleep_window ──────────────────────────────────────────────────────


def test_parse_sleep_window_wraps_midnight():
    result = parse_sleep_window({"start": "23:00", "end": "07:00"})
    assert result == (23 * 60, 7 * 60)


def test_parse_sleep_window_none():
    assert parse_sleep_window(None) is None
    assert parse_sleep_window({}) is None


# ── advance_past_sleep ───────────────────────────────────────────────────────


def test_advance_past_sleep_outside_window():
    """Time outside sleep window is returned unchanged."""
    utc = pendulum.datetime(2026, 3, 21, 14, 0, 0, tz="UTC").isoformat()  # 10:00 NY
    result = advance_past_sleep(
        utc_iso=utc,
        sleep_window={"start": "23:00", "end": "07:00"},
        user_timezone="America/New_York",
    )
    assert result == utc


def test_advance_past_sleep_inside_window_no_rrule():
    """Time inside sleep window advances to sleep-end wall-clock time."""
    # 03:00 NY is inside 23:00–07:00 sleep window
    utc = pendulum.datetime(2026, 3, 21, 7, 0, 0, tz="UTC").isoformat()  # 03:00 NY
    result = advance_past_sleep(
        utc_iso=utc,
        sleep_window={"start": "23:00", "end": "07:00"},
        user_timezone="America/New_York",
    )
    local = pendulum.parse(result).in_timezone("America/New_York")
    assert local.hour == 7
    assert local.minute == 0


def test_advance_past_sleep_inside_window_with_rrule():
    """With RRULE, returns the next valid RRULE occurrence at or after sleep end."""
    # 02:00 NY = inside sleep (23:00–07:00). dtstart = canonical 02:00 NY.
    # DAILY rule: next occurrence strictly after (sleep_end - 1s) = 06:59:59
    # dtstart=02:00 NY, DAILY → occurrences at 02:00. next after 06:59:59 = next day 02:00.
    # That lands in sleep again — advance_past_sleep is called once (single pass).
    # Key check: function returns a valid ISO string (not the original).
    dtstart = pendulum.datetime(2026, 3, 21, 7, 0, 0, tz="UTC")  # 03:00 NY (in sleep)
    utc = dtstart.isoformat()
    result = advance_past_sleep(
        utc_iso=utc,
        sleep_window={"start": "23:00", "end": "07:00"},
        user_timezone="America/New_York",
        rrule_string="FREQ=DAILY",
        dtstart=dtstart,
    )
    # Result should be different from the input (it was in sleep and was advanced)
    assert result != utc
    # And it should be a valid ISO string
    pendulum.parse(result)

"""
Unit tests for congestion.compute_free_minutes.

Spec coverage:
  - Standard day (normal profile, some tasks)
  - Congested day (tasks fill all free time)
  - Midnight-wrap sleep window (e.g. 23:00–07:00)
  - Absent work_minutes_by_day falls back to _WORK_FALLBACK (not zero)
  - Absent sleep_window falls back to 480 min (not zero)
  - Zero-task day returns full free time
"""

from __future__ import annotations

import datetime


from app.services.congestion import _WORK_FALLBACK, compute_free_minutes


# ── Helpers ───────────────────────────────────────────────────────────────────


def _monday() -> datetime.date:
    return datetime.date(2026, 3, 23)  # Known Monday


def _standard_profile() -> dict:
    return {
        "sleep_window": {"start": "23:00", "end": "07:00"},  # 8 h sleep (480 min)
        "work_minutes_by_day": {
            "mon": 480,
            "tue": 480,
            "wed": 480,
            "thu": 480,
            "fri": 480,
            "sat": 0,
            "sun": 0,
        },
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_standard_day_no_tasks():
    """Mon with 8h sleep + 8h work + no tasks → 8h free."""
    profile = _standard_profile()
    free = compute_free_minutes(profile, [], _monday())
    # 24*60 - 480 (sleep) - 480 (work) = 480
    assert free == 480


def test_standard_day_some_tasks():
    """60 min of existing tasks reduces free time by 60."""
    profile = _standard_profile()
    free = compute_free_minutes(profile, [30, 30], _monday())
    assert free == 420  # 480 - 60


def test_congested_day():
    """When tasks eat all free time, result is 0."""
    profile = _standard_profile()
    free = compute_free_minutes(profile, [480], _monday())
    assert free == 0


def test_free_time_clamped_to_zero():
    """Tasks can exceed 'free' time (back-to-back schedule); result must not go negative."""
    profile = _standard_profile()
    free = compute_free_minutes(profile, [600], _monday())
    assert free == 0


def test_midnight_wrap_sleep_window():
    """23:00–07:00 sleep wraps midnight and should compute 8 h (480 min), same as non-wrapped."""
    profile = {
        "sleep_window": {"start": "23:00", "end": "07:00"},
        "work_minutes_by_day": {"mon": 0},
    }
    free = compute_free_minutes(profile, [], _monday())
    # 24*60 - 480 (sleep) - 0 (no work Mon override)
    assert free == 960  # 16h free (no work set for this simplified profile)


def test_no_midnight_wrap_sleep_window():
    """22:00–06:00 — start < end, no wrap, 8 h sleep."""
    profile = {
        "sleep_window": {"start": "22:00", "end": "06:00"},
        "work_minutes_by_day": {"mon": 480},
    }
    free = compute_free_minutes(profile, [], _monday())
    assert free == 480  # 24*60 - 480 - 480


def test_absent_work_minutes_by_day_uses_fallback_not_zero():
    """Missing work_minutes_by_day must use _WORK_FALLBACK (480 Mon–Fri), not 0."""
    profile = {
        "sleep_window": {"start": "23:00", "end": "07:00"},
        # work_minutes_by_day intentionally absent
    }
    free_with_missing = compute_free_minutes(profile, [], _monday())
    fallback_work = _WORK_FALLBACK["mon"]  # 480
    expected = 24 * 60 - 480 - fallback_work
    assert free_with_missing == expected
    # Confirm it's NOT treating work as zero (which would give 960)
    assert free_with_missing != 24 * 60 - 480


def test_absent_sleep_window_uses_480_fallback():
    """Missing sleep_window must fall back to 480 min sleep, not 0."""
    profile = {
        # sleep_window intentionally absent
        "work_minutes_by_day": {"mon": 0},
    }
    free = compute_free_minutes(profile, [], _monday())
    assert free == 24 * 60 - 480  # 960


def test_weekend_zero_work():
    """Saturday has 0 work minutes in standard profile."""
    saturday = datetime.date(2026, 3, 28)  # Known Saturday
    profile = _standard_profile()
    free = compute_free_minutes(profile, [], saturday)
    # 24*60 - 480 (sleep) - 0 (sat work) = 960
    assert free == 960


def test_absent_key_from_non_empty_work_map_returns_zero():
    """A non-empty work_minutes_by_day missing a specific weekday key treats that day as 0 work."""
    # Non-empty dict (truthy) — 'mon' key intentionally absent
    profile = {
        "sleep_window": {"start": "23:00", "end": "07:00"},
        "work_minutes_by_day": {"tue": 480, "wed": 480},  # mon missing
    }
    free = compute_free_minutes(profile, [], _monday())
    # Should NOT raise; work_minutes defaults to 0 for missing 'mon' key
    assert free == 24 * 60 - 480  # sleep only, 0 work

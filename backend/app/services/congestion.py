"""
Congestion service — compute estimated free time on a given calendar day.

Pure functions, no DB calls, no side effects. Used by ask_start_date_node to
identify the lightest available day and disable fully-booked dates in the
calendar picker before the user picks a goal start date.
"""

import datetime

from app.services.rrule_expander import parse_sleep_window

# Default work minutes per weekday when work_minutes_by_day is absent from profile.
# 480 min = 8 h Mon–Fri; 0 on weekends.
_WORK_FALLBACK: dict[str, int] = {
    "mon": 480,
    "tue": 480,
    "wed": 480,
    "thu": 480,
    "fri": 480,
    "sat": 0,
    "sun": 0,
}

# date.weekday() returns 0=Mon … 6=Sun; map to lowercase abbreviations.
_WEEKDAY_ABBRS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def compute_free_minutes(
    profile: dict,
    task_duration_minutes_on_day: list[int],
    date: datetime.date,
) -> int:
    """
    Return estimated free minutes on *date* for a user with *profile*,
    given the total task load already scheduled on that day.

    Args:
        profile:                      User profile dict (from users.profile).
                                      Uses sleep_window and work_minutes_by_day.
        task_duration_minutes_on_day: Durations (in minutes) of all existing
                                      tasks (materialized + projected recurring)
                                      that fall on *date*.
        date:                         The calendar date to evaluate.

    Returns:
        Estimated free minutes (clamped to 0). A value ≤ min_task_duration
        means the day is congested.

    Known limitation: if sleep and work hours overlap (e.g. graveyard shift)
    the formula double-counts those minutes. Accepted as a rare edge case for
    a heuristic check.
    """
    # ── Sleep minutes ─────────────────────────────────────────────────────────
    sleep_parsed = parse_sleep_window(profile.get("sleep_window"))
    if sleep_parsed is not None:
        start_min, end_min = sleep_parsed
        if start_min >= end_min:
            # Wraps midnight (e.g. 23:00–07:00): time_asleep = (midnight-start) + end
            sleep_minutes = (24 * 60 - start_min) + end_min
        else:
            sleep_minutes = end_min - start_min
    else:
        sleep_minutes = 480  # 8-hour fallback when sleep_window absent

    # ── Work minutes ──────────────────────────────────────────────────────────
    weekday_abbr = _WEEKDAY_ABBRS[date.weekday()]  # 0=Mon … 6=Sun
    work_minutes_by_day: dict[str, int] = (
        profile.get("work_minutes_by_day") or _WORK_FALLBACK
    )
    work_minutes = work_minutes_by_day.get(weekday_abbr, 0)

    # ── Task minutes ──────────────────────────────────────────────────────────
    task_minutes = sum(task_duration_minutes_on_day)

    return max(0, 24 * 60 - sleep_minutes - work_minutes - task_minutes)

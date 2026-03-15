"""
12.1 + 12.2 — RRULE Expander (`app/services/rrule_expander.py`) — §5.

Expands a single iCal RRULE string into a list of individual task dicts,
one per occurrence. All returned scheduled_at values are UTC ISO8601 strings.
"""

from dateutil.rrule import rrulestr
import pendulum


def expand_rrule_to_tasks(
    base_task: dict,
    rrule_string: str,
    start_dt: pendulum.DateTime,
    end_dt: pendulum.DateTime,
    user_timezone: str,
) -> list[dict]:
    """
    12.1 — Expand a single RRULE into individual task dicts (one per occurrence).

    Args:
        base_task:      Shared task fields (user_id, title, goal_id, etc.).
                        scheduled_at and recurrence_rule are overwritten per occurrence.
        rrule_string:   iCal RRULE, e.g. "FREQ=WEEKLY;BYDAY=MO,WE,FR"
        start_dt:       First occurrence datetime in the USER's local timezone.
        end_dt:         Expansion horizon in the USER's local timezone.
        user_timezone:  IANA timezone string, e.g. "America/New_York".

    Returns:
        List of task dicts ready for DB insert. Each has scheduled_at as UTC ISO8601.

    12.2 — Each occurrence is treated as a local-time datetime and converted to UTC
    via pendulum before being appended to the output list. This correctly handles
    DST transitions (e.g., a weekly task at 07:00 local stays at 07:00 after the
    clock change, rather than drifting by an hour in UTC).
    """
    # dateutil rrulestr works with naive or tz-aware datetimes.
    # Pass start_dt as naive local time so occurrences are generated in local time.
    naive_start = start_dt.naive()  # strips timezone info; keeps wall-clock value
    rule = rrulestr(rrule_string, dtstart=naive_start)

    # between() is inclusive of both bounds
    naive_end = end_dt.naive()
    occurrences = rule.between(naive_start, naive_end, inc=True)

    tasks: list[dict] = []
    tz = pendulum.timezone(user_timezone)

    for occ in occurrences:
        # 12.2 — Interpret the naive occurrence as local wall-clock time, then UTC
        local_dt = pendulum.instance(occ, tz=tz)
        utc_dt = local_dt.in_timezone("UTC")

        task = {
            **base_task,
            "scheduled_at": utc_dt.isoformat(),
            "recurrence_rule": rrule_string,
        }
        tasks.append(task)

    return tasks


def occurrence_on_date(
    rrule_string: str,
    task_scheduled_at: pendulum.DateTime,
    target_date: str,
    user_timezone: str,
) -> str | None:
    """
    Return the UTC ISO8601 time of the occurrence on target_date if the
    RRULE (anchored at task_scheduled_at) has one, else None.

    Args:
        rrule_string:      iCal RRULE, e.g. "FREQ=WEEKLY;BYDAY=MO"
        task_scheduled_at: The pending row's scheduled_at (UTC or tz-aware).
        target_date:       YYYY-MM-DD in the user's local timezone.
        user_timezone:     IANA timezone string, e.g. "America/New_York".
    """
    tz = pendulum.timezone(user_timezone)

    # Use the pending row's local wall-clock time as dtstart
    local_start = task_scheduled_at.in_timezone(user_timezone)
    naive_start = local_start.naive()

    # Parse target_date as start/end of day (naive local)
    y, m, d = (int(p) for p in target_date.split("-"))
    import datetime as _dt

    start_of_day = _dt.datetime(y, m, d, 0, 0, 0)
    end_of_day = _dt.datetime(y, m, d, 23, 59, 59)

    rule = rrulestr(rrule_string, dtstart=naive_start)
    occurrences = rule.between(start_of_day, end_of_day, inc=True)

    if not occurrences:
        return None

    occ = occurrences[0]
    local_dt = pendulum.instance(occ, tz=tz)
    return local_dt.in_timezone("UTC").isoformat()


def projected_occurrences_in_window(
    rrule_string: str,
    task_scheduled_at: pendulum.DateTime,  # pending row's scheduled_at — RRULE dtstart anchor
    window_start: pendulum.DateTime,  # UTC lower bound of the planning window
    window_end: pendulum.DateTime,  # UTC upper bound of the planning window
    user_timezone: str,
) -> list[dict]:
    """
    Return virtual future occurrences of a recurring task that fall between
    window_start and window_end (both UTC). Uses task_scheduled_at as the
    RRULE dtstart anchor so the wall-clock time is preserved correctly.

    Returns a list of dicts: [{"scheduled_at": "<UTC ISO8601>", "is_projected": True}, ...]
    Returns [] if no occurrences fall in the window.
    """
    tz = pendulum.timezone(user_timezone)

    # RRULE anchor: use the pending row's local wall-clock time as dtstart.
    # e.g. a task at 07:00 every Monday stays at 07:00 even after DST.
    naive_anchor = task_scheduled_at.in_timezone(user_timezone).naive()

    # Convert UTC window bounds → naive local time for dateutil.between()
    naive_ws = window_start.in_timezone(user_timezone).naive()
    naive_we = window_end.in_timezone(user_timezone).naive()

    rule = rrulestr(rrule_string, dtstart=naive_anchor)
    result = []
    for occ in rule.between(naive_ws, naive_we, inc=True):
        utc_dt = pendulum.instance(occ, tz=tz).in_timezone("UTC")
        result.append({"scheduled_at": utc_dt.isoformat(), "is_projected": True})
    return result


def next_occurrence_after(
    rrule_string: str,
    after_dt: pendulum.DateTime,
    user_timezone: str,
) -> str | None:
    """
    Return the next occurrence of an RRULE strictly after after_dt, as a UTC ISO8601 string.

    Returns None if the RRULE has no more occurrences after after_dt.

    Args:
        rrule_string:  iCal RRULE, e.g. "FREQ=DAILY"
        after_dt:      Reference datetime (UTC or timezone-aware). The next occurrence
                       will be strictly after this point.
        user_timezone: IANA timezone string for wall-clock expansion.
    """
    tz = pendulum.timezone(user_timezone)
    local_after = after_dt.in_timezone(user_timezone)
    naive_after = local_after.naive()

    rule = rrulestr(rrule_string, dtstart=naive_after)
    occ = rule.after(naive_after, inc=False)  # strictly after
    if occ is None:
        return None

    local_dt = pendulum.instance(occ, tz=tz)
    return local_dt.in_timezone("UTC").isoformat()

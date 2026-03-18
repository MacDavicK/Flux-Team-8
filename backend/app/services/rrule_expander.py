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
    dtstart: pendulum.DateTime | None = None,
) -> str | None:
    """
    Return the next occurrence of an RRULE strictly after after_dt, as a UTC ISO8601 string.

    Returns None if the RRULE has no more occurrences after after_dt.

    Args:
        rrule_string:  iCal RRULE, e.g. "FREQ=DAILY"
        after_dt:      Reference datetime (UTC or timezone-aware). The next occurrence
                       will be strictly after this point.
        user_timezone: IANA timezone string for wall-clock expansion.
        dtstart:       Optional anchor datetime whose time-of-day is used as the rrule
                       dtstart.  Pass the task's original scheduled_at so that weekly
                       rules preserve the intended hour/minute instead of inheriting
                       the current wall-clock time.  Defaults to after_dt when omitted.
    """
    tz = pendulum.timezone(user_timezone)
    local_after = after_dt.in_timezone(user_timezone)
    naive_after = local_after.naive()

    # Use provided dtstart (preserves intended time-of-day) or fall back to after_dt.
    if dtstart is not None:
        naive_dtstart = dtstart.in_timezone(user_timezone).naive()
    else:
        naive_dtstart = naive_after

    rule = rrulestr(rrule_string, dtstart=naive_dtstart)
    occ = rule.after(naive_after, inc=False)  # strictly after
    if occ is None:
        return None

    local_dt = pendulum.instance(occ, tz=tz)
    return local_dt.in_timezone("UTC").isoformat()


# ─────────────────────────────────────────────────────────────────
# Sleep-window utilities
# ─────────────────────────────────────────────────────────────────


def parse_sleep_window(sleep_window: dict | None) -> tuple[int, int] | None:
    """
    Parse {"start": "HH:MM", "end": "HH:MM"} into (start_min, end_min) as
    minutes since midnight, or None if the dict is missing or malformed.
    """
    if not sleep_window:
        return None
    try:
        sh, sm = (int(x) for x in str(sleep_window["start"]).split(":"))
        eh, em = (int(x) for x in str(sleep_window["end"]).split(":"))
        return sh * 60 + sm, eh * 60 + em
    except Exception:
        return None


def _in_sleep(minutes: int, start_min: int, end_min: int) -> bool:
    """Return True if minutes-since-midnight falls inside the sleep window."""
    if start_min >= end_min:  # wraps midnight, e.g. 21:30–07:00
        return minutes >= start_min or minutes < end_min
    return start_min <= minutes < end_min


def advance_past_sleep(
    utc_iso: str,
    sleep_window: dict | None,
    user_timezone: str,
    rrule_string: str | None = None,
    dtstart: pendulum.DateTime | None = None,
) -> str:
    """
    If *utc_iso* falls inside *sleep_window*, return the UTC ISO8601 string of
    the first valid moment after the sleep window ends.

    For recurring tasks pass *rrule_string* (and optionally *dtstart*) so that
    the returned time is an actual occurrence of the rule rather than the bare
    sleep-end wall-clock time.

    Returns *utc_iso* unchanged when:
      - no sleep_window is configured, or
      - the time is already outside the sleep window.
    """
    parsed = parse_sleep_window(sleep_window)
    if parsed is None:
        return utc_iso

    start_min, end_min = parsed
    tz = pendulum.timezone(user_timezone)
    try:
        local_dt = pendulum.parse(utc_iso).in_timezone(tz)
    except Exception:
        return utc_iso

    tod = local_dt.hour * 60 + local_dt.minute
    if not _in_sleep(tod, start_min, end_min):
        return utc_iso

    # Build the next sleep-end wall-clock time.
    end_h, end_m = divmod(end_min, 60)
    sleep_end = local_dt.set(hour=end_h, minute=end_m, second=0, microsecond=0)
    if sleep_end <= local_dt:
        sleep_end = sleep_end.add(days=1)

    if rrule_string:
        # Find the next RRULE occurrence at or after sleep_end.
        # Subtract 1 s so that rule.after(..., inc=False) includes the exact sleep-end time.
        next_utc = next_occurrence_after(
            rrule_string=rrule_string,
            after_dt=sleep_end.subtract(seconds=1).in_timezone("UTC"),
            user_timezone=user_timezone,
            dtstart=dtstart,
        )
        return next_utc if next_utc else utc_iso
    else:
        return sleep_end.in_timezone("UTC").isoformat()

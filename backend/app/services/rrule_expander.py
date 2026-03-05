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

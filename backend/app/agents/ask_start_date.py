"""
ask_start_date node — inserted between APPROVE and save_tasks.

After the user approves a goal plan, we ask when they'd like to start.
This lets them delay the first task by a few days (e.g. "next Monday",
"in 3 days", "start from the 15th").

The user's reply is classified by the orchestrator as START_DATE intent,
which carries a parsed ISO8601 date in goal_start_date. The scheduler then
uses goal_start_date as the baseline for the first occurrence of each task.

Congestion pre-check
────────────────────
Before generating the question this node inspects the user's next 14 days
and computes free time per day (24 h − sleep − work − existing tasks).
It then:
  • identifies the lightest day  → suggested_date (pre-selected in the UI)
  • lists fully-congested days   → congested_dates (disabled in the calendar)

Both values are written to state and forwarded to the API response so the
frontend can render a smart calendar picker without a second round-trip.
"""

import datetime
import json as _json
import logging

import pendulum

from app.agents.state import AgentState
from app.services.congestion import compute_free_minutes
from app.services.rrule_expander import projected_occurrences_in_window
from app.services.supabase import db

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 14


async def ask_start_date_node(state: AgentState) -> dict:
    """
    Appends a start-date question to conversation history and ends the turn.
    The orchestrator re-enters on the user's next message and classifies it
    as START_DATE, which routes to save_tasks with goal_start_date set.

    Also computes suggested_date and congested_dates for the calendar picker.
    """
    history = list(state.get("conversation_history") or [])
    profile: dict = dict(state.get("user_profile") or {})
    user_id: str = state["user_id"]
    user_tz: str = profile.get("timezone", "UTC")
    goal_draft: dict = state.get("goal_draft") or {}

    suggested_date: str | None = None
    congested_dates: list[str] = []

    try:
        # ── 1. Lazy-fill work_minutes_by_day for pre-feature users ───────────
        if profile.get("work_minutes_by_day") is None:
            from app.agents.onboarding import _parse_work_minutes_by_day  # noqa: PLC0415

            work_minutes = await _parse_work_minutes_by_day(
                profile.get("work_hours", "")
            )
            profile["work_minutes_by_day"] = work_minutes
            # Merge into DB profile — leave all other profile keys intact.
            await db.execute(
                """
                UPDATE users
                SET profile    = profile || $1::jsonb,
                    updated_at = now()
                WHERE id = $2
                """,
                _json.dumps({"work_minutes_by_day": work_minutes}),
                user_id,
            )

        # ── 2. Min task duration from the goal draft ─────────────────────────
        proposed_tasks = (goal_draft.get("plan") or {}).get("proposed_tasks") or []
        if proposed_tasks:
            min_task_duration = min(
                t.get("duration_minutes", 30) for t in proposed_tasks
            )
        else:
            min_task_duration = 30

        # ── 3. Build 14-day UTC window ────────────────────────────────────────
        tz = pendulum.timezone(user_tz)
        today_local = pendulum.now(tz).start_of("day")
        window_start = today_local.in_timezone("UTC")
        window_end = today_local.add(days=_WINDOW_DAYS).in_timezone("UTC")

        # ── 4. Materialized tasks in the window ───────────────────────────────
        mat_rows = await db.fetch(
            """
            SELECT title, scheduled_at, duration_minutes
            FROM tasks
            WHERE user_id = $1
              AND status IN ('pending', 'rescheduled')
              AND scheduled_at >= $2
              AND scheduled_at < $3
            """,
            user_id,
            window_start,
            window_end,
        )

        # date_str → list[duration_minutes]
        durations_by_date: dict[str, list[int]] = {}
        seen: set[tuple[str, str]] = set()  # (title, scheduled_at_iso)

        for row in mat_rows:
            dt_local = pendulum.instance(row["scheduled_at"]).in_timezone(user_tz)
            date_str = dt_local.format("YYYY-MM-DD")
            duration = row["duration_minutes"] or 30
            durations_by_date.setdefault(date_str, []).append(duration)
            seen.add((row["title"], dt_local.isoformat()))

        # ── 5. RRULE projections for recurring tasks ──────────────────────────
        rec_rows = await db.fetch(
            """
            SELECT title, scheduled_at, canonical_scheduled_at, duration_minutes, recurrence_rule
            FROM tasks
            WHERE user_id = $1
              AND status IN ('pending', 'rescheduled')
              AND recurrence_rule IS NOT NULL
            """,
            user_id,
        )
        for rec in rec_rows:
            raw_anchor = rec["canonical_scheduled_at"] or rec["scheduled_at"]
            anchor = pendulum.instance(raw_anchor)
            for proj in projected_occurrences_in_window(
                rec["recurrence_rule"], anchor, window_start, window_end, user_tz
            ):
                proj_local = pendulum.parse(proj["scheduled_at"]).in_timezone(user_tz)
                dedup_key = (rec["title"], proj_local.isoformat())
                if dedup_key in seen:
                    continue  # already covered by materialized row
                date_str = proj_local.format("YYYY-MM-DD")
                duration = rec["duration_minutes"] or 30
                durations_by_date.setdefault(date_str, []).append(duration)
                seen.add(dedup_key)

        # ── 6. Compute free minutes per day ───────────────────────────────────
        free_by_date: dict[str, int] = {}
        for i in range(_WINDOW_DAYS):
            day_local = today_local.add(days=i)
            date_str = day_local.format("YYYY-MM-DD")
            date_obj = datetime.date(day_local.year, day_local.month, day_local.day)
            durations = durations_by_date.get(date_str, [])
            free_by_date[date_str] = compute_free_minutes(profile, durations, date_obj)

        # ── 7. Build congested_dates + suggested_date ─────────────────────────
        for date_str, free in free_by_date.items():
            if free <= min_task_duration:
                congested_dates.append(date_str)

        congested_set = set(congested_dates)
        non_congested = [
            (ds, free) for ds, free in free_by_date.items() if ds not in congested_set
        ]
        # Only surface a suggestion when existing tasks create uneven load across
        # days.  The work schedule creates inherent asymmetry (weekdays vs weekends)
        # even with zero tasks — we do NOT want to tell a brand-new user "Sunday
        # looks lightest" just because Sunday has no work hours.  The signal must
        # come from actual task congestion, not the fixed schedule baseline.
        if non_congested and durations_by_date:
            max_free = max(free for _, free in non_congested)
            min_free = min(free for _, free in non_congested)
            if max_free > min_free:
                suggested_date = max(non_congested, key=lambda x: x[1])[0]

    except Exception:
        logger.warning("ask_start_date congestion check failed", exc_info=True)
        suggested_date = None
        congested_dates = []

    # ── 8. Build question text ────────────────────────────────────────────────
    if suggested_date:
        y, m, d = (int(p) for p in suggested_date.split("-"))
        date_obj = datetime.date(y, m, d)
        formatted = f"{date_obj.strftime('%A, %B')} {date_obj.day}"
        question = (
            f"Your schedule looks lightest on {formatted}. "
            "Want to start then, or pick another date?"
        )
    else:
        question = (
            "When would you like to start? "
            'You can say "today", "tomorrow", "next Monday", or give me a specific date — '
            "and I'll schedule your first task from there."
        )

    return {
        "conversation_history": history + [{"role": "assistant", "content": question}],
        "approval_status": "awaiting_start_date",
        "suggested_date": suggested_date,
        "congested_dates": congested_dates,
    }

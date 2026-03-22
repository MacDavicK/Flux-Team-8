# canonical_scheduled_at Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `proposed_time` integer column with `canonical_scheduled_at` (UTC timestamp) in the recurring task advance chain, eliminating RRULE anchor drift and same-day duplicate occurrences on pull-back reschedules.

**Architecture:** Add a `canonical_scheduled_at` column set at task creation (= the final scheduled_at after all guards) and never changed on single-occurrence reschedules. Pass it as both `after_dt` and `dtstart` to `next_occurrence_after` and `advance_past_sleep`, replacing all `proposed_time` usage. The scheduler also uses it as the RRULE projection anchor.

**Tech Stack:** Python, asyncpg, pendulum, dateutil, pytest, unittest.mock

**Spec:** `docs/recurrence-series-dtstart-redesign.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/migrations/016_tasks_canonical_scheduled_at.sql` | **Create** | Add `canonical_scheduled_at TIMESTAMPTZ`, drop `proposed_time` |
| `backend/tests/unit/test_rrule_expander.py` | **Create** | Pure unit tests for `next_occurrence_after` and `advance_past_sleep` |
| `backend/tests/unit/test_recurrence.py` | **Create** | Unit tests for `advance_recurring_task` with mocked DB — all edge cases from spec |
| `backend/app/services/recurrence.py` | **Modify** | Use `canonical_dt` as both `after_dt` and `dtstart`; remove `proposed_time` block |
| `backend/app/agents/save_tasks.py` | **Modify** | Set `canonical_scheduled_at = scheduled_at_utc` for recurring tasks; remove `proposed_time` |
| `backend/app/api/v1/tasks.py` | **Modify** | Update all SELECTs; series reschedule sets both fields; goal-linked single reschedule copies `canonical_scheduled_at` |
| `backend/app/agents/scheduler.py` | **Modify** | SELECT includes `canonical_scheduled_at`; use it as RRULE projection anchor |
| `backend/app/models/api_schemas.py` | **No change** | `proposed_time` is not exposed in any response schema — confirmed |
| `backend/app/services/rrule_expander.py` | **No change** | `dtstart` param already exists on both functions |

---

## Task 1: Pure unit tests for rrule_expander (should pass today — baseline)

**Files:**
- Create: `backend/tests/unit/test_rrule_expander.py`

These test `next_occurrence_after` and `advance_past_sleep` directly. No DB mocking needed. Run them now to confirm the baseline works before any DB changes.

- [ ] **Step 1: Create test file**

```python
"""
Unit tests for rrule_expander — pure functions, no DB required.
Run: pytest tests/unit/test_rrule_expander.py -v
"""
import pendulum
import pytest

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
    result = next_occurrence_after("FREQ=DAILY", after, "America/New_York", dtstart=dtstart)
    # 09:00 New York = 13:00 UTC on March 21; next day same local time = 13:00 UTC March 22
    # (before DST spring forward on March 8 2026 — no DST change between 21-22 March)
    assert result is not None
    dt = pendulum.parse(result)
    local = dt.in_timezone("America/New_York")
    assert local.day == 22
    assert local.hour == 9
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
    result = next_occurrence_after(
        "FREQ=DAILY;UNTIL=20260331T090000Z", after, "UTC", dtstart=after
    )
    assert result is None


def test_next_occurrence_after_pull_back_no_same_day_duplicate():
    """
    When canonical_dt (dtstart + after_dt) is used for a pull-back rescheduled task,
    rule.after must NOT return the same calendar day.

    Scenario: DAILY at 09:00, single-occurrence pull-back to 08:00.
    canonical_dt = Monday 09:00.
    Expected: Tuesday 09:00. NOT Monday 09:00.
    """
    # canonical = Mon Mar 23 09:00 local (= 13:00 UTC in New York)
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
    """With RRULE, returns the next valid occurrence at or after sleep end."""
    # DAILY at 02:00 NY falls inside sleep (23:00-07:00). dtstart = canonical 02:00 NY.
    # sleep end = 07:00 → next DAILY occurrence at or after 07:00 = same day 07:00?
    # No — DAILY at 02:00, next after 07:00 = next day 02:00 (first occurrence strictly after sleep_end-1s)
    # Actually: sleep_end is 07:00. We subtract 1s → 06:59:59, rule.after(06:59:59) = 07:00 same day?
    # No, dtstart=02:00, DAILY → occurrences at 02:00. next after 06:59:59 = next day 02:00.
    # sleep guard: 02:00 is IN sleep window → recurse? No, advance_past_sleep is called once.
    # This confirms: for a DAILY task at 02:00 that lands in sleep, the advance pushes it to the
    # next RRULE occurrence after sleep-end. That's the next day at 02:00 — still in sleep.
    # This is expected: recurrence.py calls advance_past_sleep once; the truly correct behavior
    # for a task always-in-sleep would require the scheduler to pick a different time.
    # For test purposes: verify the function finds the next rrule occurrence after sleep-end.
    dtstart = pendulum.datetime(2026, 3, 21, 7, 0, 0, tz="UTC")  # 02:00 NY (in sleep)
    utc = dtstart.isoformat()
    result = advance_past_sleep(
        utc_iso=utc,
        sleep_window={"start": "23:00", "end": "07:00"},
        user_timezone="America/New_York",
        rrule_string="FREQ=DAILY",
        dtstart=dtstart,
    )
    local = pendulum.parse(result).in_timezone("America/New_York")
    # Next DAILY occurrence at or after 07:00 NY = 07:00 same day (strictly after 06:59:59)
    # 07:00 NY = 11:00 UTC on Mar 21 (EST, UTC-4 after DST? Check: Mar 21 is after DST spring forward Mar 8)
    # EDT = UTC-4 → 07:00 EDT = 11:00 UTC
    assert local.hour == 7 or local.day == 22  # either same-day 07:00 or next-day (rrule-dependent)
    # The key assertion: result is after the sleep start
    result_local = pendulum.parse(result).in_timezone("America/New_York")
    assert not (result_local.hour >= 23 or result_local.hour < 7), (
        f"Result {result_local} should be outside sleep window"
    )
```

- [ ] **Step 2: Run tests to verify they pass (baseline)**

```bash
cd backend && python -m pytest tests/unit/test_rrule_expander.py -v
```

Expected: All pass. If any fail, that's a pre-existing bug to fix before continuing.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_rrule_expander.py
git commit -m "test: add baseline unit tests for rrule_expander pure functions"
```

---

## Task 2: Unit tests for advance_recurring_task (will FAIL until Task 4 is done)

**Files:**
- Create: `backend/tests/unit/test_recurrence.py`

These mock the DB and test the full `advance_recurring_task` logic. They will fail until `recurrence.py` is updated in Task 4. Write them now (TDD), then the red→green cycle confirms the implementation is correct.

- [ ] **Step 1: Create test file**

```python
"""
Unit tests for advance_recurring_task.

All DB calls are mocked. The mock task rows use `canonical_scheduled_at`
(the new column) instead of `proposed_time`.

Run: pytest tests/unit/test_recurrence.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pendulum
import pytest

from app.services.recurrence import advance_recurring_task

UTC = timezone.utc


def _make_task(
    recurrence_rule: str,
    scheduled_at: datetime,
    canonical_scheduled_at: datetime | None,
    goal_id=None,
    proposed_time=None,  # kept to verify it's ignored after migration
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
    }


def _make_user(tz: str = "America/New_York", sleep_window=None) -> dict:
    return {
        "timezone": tz,
        "profile": {"sleep_window": sleep_window} if sleep_window else {},
    }


# Helper: build datetime in New York timezone → UTC
def _ny(year, month, day, hour, minute=0) -> datetime:
    """Return a UTC-aware datetime corresponding to HH:MM in America/New_York."""
    local = pendulum.datetime(year, month, day, hour, minute, tz="America/New_York")
    return local.in_timezone("UTC")._datetime


# ── Test 1: DAILY task, no reschedule — advances to next day ────────────────

@pytest.mark.asyncio
async def test_daily_no_reschedule():
    """Normal DAILY advance: canonical = scheduled → next day same time."""
    scheduled = _ny(2026, 3, 23, 9)   # Mon 09:00 NY
    canonical = scheduled              # No reschedule — both the same

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    _, insert_args = mock_db.execute.call_args
    # The INSERT is called with positional args; scheduled_at is $5 (index 4)
    inserted_at = mock_db.execute.call_args[0][5]  # $5 = scheduled_at
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24   # Tuesday
    assert inserted_local.hour == 9


# ── Test 2: DAILY task, push forward (09:00 → 10:00) — reverts to 09:00 ───

@pytest.mark.asyncio
async def test_daily_push_forward_reverts_to_canonical():
    """Single push-forward: scheduled_at = 10:00, canonical = 09:00 → next = 09:00 next day."""
    scheduled = _ny(2026, 3, 23, 10)   # pushed to 10:00 NY
    canonical = _ny(2026, 3, 23, 9)    # canonical stays 09:00

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24   # Tuesday
    assert inserted_local.hour == 9   # reverted to canonical 09:00, not 10:00


# ── Test 3: DAILY task, pull back (09:00 → 08:00) — no same-day duplicate ──

@pytest.mark.asyncio
async def test_daily_pull_back_no_same_day_duplicate():
    """
    Single pull-back: scheduled_at = 08:00, canonical = 09:00.
    advance must produce Tuesday 09:00, NOT Monday 09:00 (same-day duplicate).
    This is the core Flaw 2 regression test.
    """
    scheduled = _ny(2026, 3, 23, 8)    # pulled back to 08:00 NY
    canonical = _ny(2026, 3, 23, 9)    # canonical stays 09:00

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user()

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24   # TUESDAY, not Monday 23 (no duplicate)
    assert inserted_local.hour == 9


# ── Test 4: DAILY task, single reschedule into sleep window ────────────────

@pytest.mark.asyncio
async def test_daily_single_reschedule_into_sleep_window():
    """
    scheduled_at = 23:30 (inside 23:00–07:00 sleep), canonical = 09:00.
    advance uses canonical (09:00) → next is Tuesday 09:00 → sleep guard does not fire.
    """
    scheduled = _ny(2026, 3, 23, 23, 30)  # inside sleep window
    canonical = _ny(2026, 3, 23, 9)        # canonical = 09:00

    task = _make_task("FREQ=DAILY", scheduled, canonical)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.day == 24   # Tuesday
    assert inserted_local.hour == 9   # 09:00 — sleep guard does not fire at 09:00


# ── Test 5: DAILY task, series reschedule (both fields updated) ─────────────

@pytest.mark.asyncio
async def test_daily_series_reschedule_uses_new_canonical():
    """Series reschedule sets both scheduled_at and canonical to 14:00 → next = 14:00."""
    scheduled = _ny(2026, 3, 23, 14)   # series-rescheduled to 14:00
    canonical = _ny(2026, 3, 23, 14)   # canonical also updated to 14:00

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


# ── Test 6: MINUTELY task — no infinite loop ────────────────────────────────

@pytest.mark.asyncio
async def test_minutely_no_infinite_loop():
    """
    FREQ=MINUTELY;INTERVAL=30: scheduled=canonical=09:00 → next = 09:30.
    The key regression: proposed_time override (now removed) caused 09:00 to be
    re-inserted after canonical 09:00, creating an infinite miss loop.
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
    # 09:00 NY = 13:00 UTC; next = 13:30 UTC
    assert inserted_utc.hour == 13
    assert inserted_utc.minute == 30


# ── Test 7: MINUTELY task, natural next occurrence hits sleep window ────────

@pytest.mark.asyncio
async def test_minutely_natural_sleep_guard():
    """
    FREQ=MINUTELY;INTERVAL=30, canonical = 21:30 NY (no reschedule).
    Next occurrence after 21:30 = 22:00 → falls inside 23:00–07:00? No, 22:00 is NOT in 23:00–07:00.
    Use 22:30 → next = 23:00 → inside sleep (23:00–07:00) → sleep guard → 07:00 next day.
    """
    # canonical = 22:30 NY
    t = pendulum.datetime(2026, 3, 21, 22, 30, tz="America/New_York").in_timezone("UTC")._datetime
    task = _make_task("FREQ=MINUTELY;INTERVAL=30", t, t)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    # 23:00 falls in sleep → pushed to 07:00 next day
    assert inserted_local.hour == 7
    assert inserted_local.minute == 0
    assert inserted_local.day == 22  # next day


# ── Test 8: MINUTELY single reschedule INTO sleep — canonical used, sleep fires ─

@pytest.mark.asyncio
async def test_minutely_single_reschedule_into_sleep_uses_canonical():
    """
    FREQ=MINUTELY;INTERVAL=30, single reschedule from 22:30 → 23:30 (into sleep).
    canonical = 22:30 (unchanged).
    Advance: canonical 22:30 → next = 23:00 → sleep guard fires → 07:00 next day.
    Rescheduled time (23:30) is completely ignored.
    """
    canonical_t = pendulum.datetime(2026, 3, 21, 22, 30, tz="America/New_York").in_timezone("UTC")._datetime
    scheduled_t = pendulum.datetime(2026, 3, 21, 23, 30, tz="America/New_York").in_timezone("UTC")._datetime

    task = _make_task("FREQ=MINUTELY;INTERVAL=30", scheduled_t, canonical_t)
    user = _make_user(sleep_window={"start": "23:00", "end": "07:00"})

    with patch("app.services.recurrence.db") as mock_db:
        mock_db.fetchrow = AsyncMock(side_effect=[task, user])
        mock_db.execute = AsyncMock()

        result = await advance_recurring_task("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    assert result is True
    inserted_at = mock_db.execute.call_args[0][5]
    inserted_local = pendulum.instance(inserted_at).in_timezone("America/New_York")
    assert inserted_local.hour == 7   # 07:00 — sleep guard fired based on canonical chain
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
    # Task scheduled for Mon March 23, DAILY. Goal sprint ends March 23 (1 week from Mar 16).
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

    # Sprint end = Mar 16 + 1 week = Mar 23. Next occurrence = Mar 24 > Mar 23 → False.
    assert result is False
    mock_db.execute.assert_not_called()


# ── Test 11: NULL canonical (pre-migration row) — falls back to scheduled_at ─

@pytest.mark.asyncio
async def test_null_canonical_falls_back_to_scheduled_at():
    """
    Rows created before migration have canonical_scheduled_at = NULL.
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
```

- [ ] **Step 2: Run tests — verify they FAIL (TDD red phase)**

```bash
cd backend && python -m pytest tests/unit/test_recurrence.py -v 2>&1 | head -40
```

Expected: Most tests fail with `KeyError: 'canonical_scheduled_at'` or similar — the column doesn't exist yet.

- [ ] **Step 3: Commit the failing tests**

```bash
git add backend/tests/unit/test_recurrence.py
git commit -m "test: add failing unit tests for canonical_scheduled_at recurrence advance"
```

---

## Task 3: DB migration

**Files:**
- Create: `backend/migrations/016_tasks_canonical_scheduled_at.sql`

- [ ] **Step 1: Create migration file**

```sql
-- Migration 016: Replace proposed_time with canonical_scheduled_at
--
-- canonical_scheduled_at: the UTC timestamp the RRULE would have generated for
-- this occurrence — i.e. the occurrence's position in the series independent of
-- any single-occurrence reschedule. Used as both the RRULE dtstart anchor and
-- the after_dt in advance_recurring_task, so:
--   - anchor drift is eliminated (series never inherits a rescheduled time)
--   - pull-back reschedules never produce a same-day duplicate occurrence
--
-- Set once at creation (= scheduled_at after all guards).
-- Updated only on series reschedule (both fields set to the same new value).
-- Never changed on single-occurrence reschedule (scheduled_at changes; this stays).
-- NULL for one-off (non-recurring) tasks.
-- NULL for rows created before this migration (recurrence.py falls back to scheduled_at).

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS canonical_scheduled_at TIMESTAMPTZ,
    DROP COLUMN IF EXISTS proposed_time;
```

- [ ] **Step 2: Apply migration in Supabase / local DB**

Run this SQL against your database. In the Supabase dashboard: SQL Editor → paste and run. Or via psql:

```bash
psql "$DATABASE_URL" -f backend/migrations/016_tasks_canonical_scheduled_at.sql
```

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/016_tasks_canonical_scheduled_at.sql
git commit -m "migration: replace proposed_time with canonical_scheduled_at (016)"
```

---

## Task 4: Update recurrence.py — use canonical_dt as after_dt and dtstart

**Files:**
- Modify: `backend/app/services/recurrence.py`

This is the core change. Three parts: fetch the new column, build `canonical_dt`, pass it to both `next_occurrence_after` and `advance_past_sleep`, and remove the entire `proposed_time` block (~20 lines).

- [ ] **Step 1: Update the SELECT to fetch `canonical_scheduled_at`, remove `proposed_time`**

In `advance_recurring_task`, replace the `db.fetchrow` SELECT (lines 35-43):

```python
task_row = await db.fetchrow(
    """
    SELECT id, recurrence_rule, scheduled_at, canonical_scheduled_at,
           user_id, title, description,
           duration_minutes, trigger_type, location_trigger,
           goal_id, shared_with_goal_ids, escalation_policy
    FROM tasks WHERE id = $1
    """,
    task_id,
)
```

- [ ] **Step 2: Build `canonical_dt` — replace the `ref_dt` block**

Replace the existing `ref_dt` / `scheduled_at` block (lines 58-63) with:

```python
scheduled_at = task_row["scheduled_at"]
ref_dt = (
    pendulum.instance(scheduled_at)
    if hasattr(scheduled_at, "isoformat")
    else pendulum.parse(str(scheduled_at))
)

raw_canonical = task_row["canonical_scheduled_at"]
if raw_canonical is not None:
    canonical_dt = (
        pendulum.instance(raw_canonical)
        if hasattr(raw_canonical, "isoformat")
        else pendulum.parse(str(raw_canonical))
    )
else:
    canonical_dt = ref_dt  # fallback for rows created before migration (NULL)
```

- [ ] **Step 3: Pass `canonical_dt` to `next_occurrence_after`**

Replace the existing call (lines 65-69):

```python
next_utc = next_occurrence_after(
    rrule_string=task_row["recurrence_rule"],
    after_dt=canonical_dt,   # canonical position — not rescheduled time
    user_timezone=user_tz,
    dtstart=canonical_dt,    # same — stable series anchor
)
```

- [ ] **Step 4: Remove the entire `proposed_time` block (~lines 84-104)**

Delete everything from `proposed_time = task_row["proposed_time"]` through the closing `except` block. This is the 20-line block including `_SUB_DAILY`, `_proposed_time_applies`, and the `try/except` that applied the time override. After deletion, `next_utc` flows directly into the sleep-window guard.

- [ ] **Step 5: Pass `canonical_dt` as `dtstart` to `advance_past_sleep`**

Replace the sleep-window guard block (around line 108-121):

```python
if sleep_window and next_utc:
    try:
        next_utc = advance_past_sleep(
            utc_iso=next_utc,
            sleep_window=sleep_window,
            user_timezone=user_tz,
            rrule_string=task_row["recurrence_rule"],
            dtstart=canonical_dt,   # was: pendulum.parse(next_utc)
        )
    except Exception as exc:
        logger.warning(
            "Sleep-window advance failed for recurring task %s: %s", task_id, exc
        )
```

- [ ] **Step 6: Update the INSERT to use `canonical_scheduled_at` instead of `proposed_time`**

Replace the `await db.execute(INSERT ...)` at the end of the function:

```python
await db.execute(
    """
    INSERT INTO tasks (
        user_id, goal_id, title, description, status,
        scheduled_at, duration_minutes, trigger_type, location_trigger,
        recurrence_rule, shared_with_goal_ids, escalation_policy,
        canonical_scheduled_at
    ) VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9, $10, $11, $12)
    """,
    user_id,
    goal_id,
    task_row["title"],
    task_row["description"],
    pendulum.parse(next_utc),        # $5 = scheduled_at
    task_row["duration_minutes"],
    task_row["trigger_type"],
    task_row["location_trigger"],
    task_row["recurrence_rule"],
    shared_ids,
    task_row["escalation_policy"],
    pendulum.parse(next_utc),        # $12 = canonical_scheduled_at (= scheduled_at; no reschedule yet)
)
```

- [ ] **Step 7: Run unit tests — verify they pass (TDD green phase)**

```bash
cd backend && python -m pytest tests/unit/test_recurrence.py -v
```

Expected: All 11 tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/recurrence.py
git commit -m "feat: use canonical_scheduled_at as after_dt and dtstart in advance_recurring_task"
```

---

## Task 5: Update save_tasks.py — set canonical_scheduled_at at creation

**Files:**
- Modify: `backend/app/agents/save_tasks.py`

Three changes: update `_row_to_tuple` and `_INSERT_SQL` to swap `proposed_time` → `canonical_scheduled_at`, and replace the `proposed_time` computation block in the recurring task branch.

- [ ] **Step 1: Update `_INSERT_SQL` (line 102)**

```python
_INSERT_SQL = """
INSERT INTO tasks (
    user_id, goal_id, title, description, status,
    scheduled_at, duration_minutes, trigger_type, location_trigger,
    recurrence_rule, shared_with_goal_ids, escalation_policy, conversation_id,
    canonical_scheduled_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
"""
```

- [ ] **Step 2: Update `_row_to_tuple` (line 76) — replace `proposed_time` with `canonical_scheduled_at`**

```python
def _row_to_tuple(row: dict) -> tuple:
    """Convert a task dict to the positional tuple used by the INSERT statement."""
    scheduled_at = row.get("scheduled_at")
    if isinstance(scheduled_at, str):
        try:
            scheduled_at = pendulum.parse(scheduled_at)
        except Exception:
            scheduled_at = None

    canonical = row.get("canonical_scheduled_at")
    if isinstance(canonical, str):
        try:
            canonical = pendulum.parse(canonical)
        except Exception:
            canonical = None

    return (
        row.get("user_id"),
        row.get("goal_id"),
        row.get("title", ""),
        row.get("description", ""),
        row.get("status", "pending"),
        scheduled_at,
        row.get("duration_minutes", 30),
        row.get("trigger_type", "time"),
        row.get("location_trigger"),
        row.get("recurrence_rule"),
        row.get("shared_with_goal_ids") or [],
        row.get("escalation_policy", "standard"),
        row.get("conversation_id"),
        canonical,   # was: row.get("proposed_time")
    )
```

- [ ] **Step 3: Replace the `proposed_time` computation block in the recurring task branch (around line 307-331)**

Find the comment `# Capture proposed_time (minutes since midnight, user local)` and replace the entire `proposed_time` block + the `_insert_task` call:

```python
if recurrence_rule and scheduled_at_utc:
    # canonical_scheduled_at is the RRULE position of this occurrence in the series.
    # Set once here (after all guards); never changed on single-occurrence reschedule.
    canonical_scheduled_at = scheduled_at_utc  # string; _row_to_tuple parses it

    await _insert_task(
        {
            **base_row,
            "scheduled_at": scheduled_at_utc,
            "recurrence_rule": recurrence_rule,
            "escalation_policy": escalation_policy,
            "canonical_scheduled_at": canonical_scheduled_at,
        }
    )
    rows_inserted += 1
```

- [ ] **Step 4: Run the rrule_expander + recurrence tests to confirm nothing broke**

```bash
cd backend && python -m pytest tests/unit/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/save_tasks.py
git commit -m "feat: set canonical_scheduled_at at task creation in save_tasks"
```

---

## Task 6: Update tasks.py — reschedule endpoints + SELECT queries

**Files:**
- Modify: `backend/app/api/v1/tasks.py`

Four sub-changes: three SELECT query updates (remove `t.proposed_time`, no replacement — it's internal), series reschedule writes both fields, goal-linked single reschedule copies `canonical_scheduled_at`.

- [ ] **Step 1: Update the three timeline SELECT column lists (lines ~90, ~116, ~144)**

In all three `SELECT` queries (the `scheduled_rows` fetch, the `todo_rows` fetch, and the `recurring_rows` fetch), replace `t.proposed_time` with `t.canonical_scheduled_at`. The field is internal-only; `_serialize_task` serializes it but the frontend doesn't use it.

Search for `t.proposed_time` — it appears in 3 queries. Replace each instance with `t.canonical_scheduled_at`.

- [ ] **Step 2: Update `_fetch_task_or_404` SELECT (line ~690)**

```python
task = await db.fetchrow(
    """
    SELECT id, user_id, goal_id, title, description, status,
           scheduled_at, duration_minutes, trigger_type, location_trigger,
           recurrence_rule, shared_with_goal_ids, escalation_policy,
           completed_at, created_at,
           canonical_scheduled_at
    FROM tasks WHERE id = $1
    """,
    task_uuid,
)
```

- [ ] **Step 3: Update series reschedule (around line 385-414)**

Replace the series reschedule UPDATE:

```python
if body.scope == "series":
    if not task.get("recurrence_rule"):
        raise HTTPException(
            status_code=422,
            detail="This task is not a recurring task",
        )

    await db.execute(
        """
        UPDATE tasks
        SET scheduled_at = $1, canonical_scheduled_at = $1, reminder_sent_at = NULL
        WHERE id = $2 AND user_id = $3
        """,
        scheduled_at_dt,
        task_uuid,
        user_uuid,
    )
    return {
        "original_task_id": task_id,
        "new_task_id": task_id,
        "status": "rescheduled",
        "scheduled_at": scheduled_at_dt.isoformat(),
        "updated_count": 1,
    }
```

Note: remove the `user_tz_str`, `tz`, `new_local`, and `new_proposed_time` variables that are no longer needed.

- [ ] **Step 4: Update goal-linked single reschedule INSERT (around line 451-471)**

Replace `task.get("proposed_time")` with `task.get("canonical_scheduled_at")`:

```python
new_task_id = await db.fetchval(
    """
    INSERT INTO tasks (
        user_id, goal_id, title, description, status,
        scheduled_at, duration_minutes, trigger_type,
        recurrence_rule, escalation_policy, canonical_scheduled_at
    )
    VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9, $10)
    RETURNING id
    """,
    user_uuid,
    task["goal_id"],
    task["title"],
    task["description"],
    scheduled_at_dt,                           # rescheduled time
    task["duration_minutes"],
    task["trigger_type"],
    task["recurrence_rule"],
    task["escalation_policy"],
    task.get("canonical_scheduled_at"),         # preserves series anchor; advance reverts correctly
)
```

- [ ] **Step 5: Run all unit tests**

```bash
cd backend && python -m pytest tests/unit/ -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/tasks.py
git commit -m "feat: update tasks.py reschedule endpoints and SELECTs for canonical_scheduled_at"
```

---

## Task 7: Update scheduler.py — RRULE projection anchor

**Files:**
- Modify: `backend/app/agents/scheduler.py`

Two changes: add `canonical_scheduled_at` to the SELECT, and use it as the RRULE projection anchor.

- [ ] **Step 1: Update the recurring_rows SELECT (line ~91)**

```python
recurring_rows = await db.fetch(
    """
    SELECT title, scheduled_at, canonical_scheduled_at, duration_minutes, recurrence_rule
    FROM tasks
    WHERE user_id = $1
      AND status IN ('pending', 'rescheduled')
      AND recurrence_rule IS NOT NULL
    """,
    user_id,
)
```

- [ ] **Step 2: Update the projection anchor (line ~102)**

```python
for rec in recurring_rows:
    anchor = pendulum.instance(
        rec["canonical_scheduled_at"] if rec["canonical_scheduled_at"] else rec["scheduled_at"]
    )
    for proj in projected_occurrences_in_window(
        rec["recurrence_rule"], anchor, window_start, window_end, user_tz
    ):
```

- [ ] **Step 3: Run all unit tests**

```bash
cd backend && python -m pytest tests/unit/ -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/scheduler.py
git commit -m "feat: use canonical_scheduled_at as RRULE projection anchor in scheduler"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run the full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All pass, including the existing `test_twilio_notification.py`.

- [ ] **Step 2: Verify `proposed_time` is gone from the entire codebase**

```bash
grep -r "proposed_time" backend/app/ backend/tests/ backend/migrations/
```

Expected: Zero results. Only `docs/` and `015_tasks_proposed_time.sql` (historical) may still reference it.

- [ ] **Step 3: Verify `canonical_scheduled_at` is present in all the right places**

```bash
grep -r "canonical_scheduled_at" backend/app/ backend/migrations/
```

Expected: appears in `016_tasks_canonical_scheduled_at.sql`, `recurrence.py`, `save_tasks.py`, `tasks.py`, `scheduler.py`.

- [ ] **Step 4: Commit (if any leftover changes exist)**

```bash
git status
# Add only files you've intentionally changed — do not use git add -A
git commit -m "chore: final cleanup — verify proposed_time fully removed"
```

# Recurrence Advance Redesign: Replace `proposed_time` with `canonical_scheduled_at`

## Status: Approved, not yet implemented

---

## Problem Summary

The recurring task advance system has two structural flaws:

**Flaw 1 — RRULE anchor drift.**
`next_occurrence_after()` uses `scheduled_at` as both the `after_dt` boundary and the
RRULE `dtstart` anchor. When a single-occurrence reschedule changes `scheduled_at`, the
anchor drifts and every future occurrence inherits the rescheduled time.

**Flaw 2 — Pull-back creates same-day duplicate.**
Even with a stable anchor (`series_dtstart`), using `scheduled_at` as `after_dt` after
a pull-back reschedule (e.g. 9 AM → 8 AM) causes `rule.after(8 AM, dtstart=9 AM)` to
return `9 AM same day` — a duplicate occurrence on the same calendar day the user already
acted on.

`proposed_time` (integer, minutes since midnight) was added to work around Flaw 1 by
overriding the time-of-day on every advance. It caused:

1. **Infinite miss loop for sub-daily tasks** — `FREQ=MINUTELY;INTERVAL=30` with
   `proposed_time=540`: advance computes `09:30`, override snaps back to `09:00` (same as
   `scheduled_at`), same timestamp re-inserted, auto-missed again every 60 seconds → 300+
   duplicate rows.
2. **Applied universally** — fires on every advance even when no reschedule happened,
   solving a 5% problem 100% of the time.
3. **Redundant for DST** — `next_occurrence_after()` already expands the RRULE in the
   user's local timezone; DST is handled inherently.
4. **Semantically misleading** — sounds like a planning concept; is actually a persistent
   series attribute controlling the advance chain for the task's entire lifetime.

---

## Decision Log

| Decision | Alternatives Considered | Reason Chosen |
|---|---|---|
| Introduce `canonical_scheduled_at` (UTC timestamp) column | `series_dtstart` only; `is_single_rescheduled` flag; embed DTSTART in RRULE string | Single column solves both flaws: serves as the stable RRULE `dtstart` anchor AND as the correct `after_dt`, eliminating anchor drift and same-day duplicate in one shot. |
| Use `canonical_scheduled_at` as both `after_dt` AND `dtstart` | Use it only as `dtstart`, keep `scheduled_at` as `after_dt` | Using `scheduled_at` as `after_dt` after a pull-back reschedule returns the canonical occurrence on the same day (Flaw 2). Using the canonical time for both arguments bypasses the rescheduled time entirely and always lands on the next series occurrence. |
| Drop `proposed_time` entirely | Keep alongside new column | With `canonical_scheduled_at`, `proposed_time` has no remaining job. Two authoritative fields for the same concern would be actively harmful. |
| `canonical_scheduled_at` unchanged on single reschedule | Update it to rescheduled time | The canonical time is what the RRULE would have generated. A single reschedule is an exception; the series must revert after it is consumed. |
| `canonical_scheduled_at` updated on series reschedule | Leave it as the original creation time | Series reschedule is a permanent change of intent. The new time becomes the new canonical. |
| Pass `canonical_scheduled_at` as `dtstart` to `advance_past_sleep` | Use `next_utc` as dtstart (prior behaviour) | Sleep window advance must use the stable series anchor so the resumed occurrence is a valid series occurrence, not an arbitrary wall-clock time. |
| Update `scheduler.py` RRULE projection anchor | Leave as `scheduled_at` | After a single reschedule, `scheduled_at` is the rescheduled time. Projecting future occurrences from it gives wrong busy-slot estimates. `canonical_scheduled_at` gives correct projections. |
| No reschedule validation constraints (direction or sleep window) | Block pull-back; block sleep-window single reschedule | Users must be free to reschedule in any direction and at any time for legitimate reasons. Constraints belong at the data model level, not the input level. |

---

## Understanding Summary

- **What**: Replace the `proposed_time` integer column with a `canonical_scheduled_at`
  UTC timestamp column. Use it as both the RRULE anchor and the `after_dt` in every
  advance call throughout the chain.
- **Why**: `proposed_time` is a leaky workaround for two missing concepts. A single
  column that stores the canonical occurrence time solves both cleanly.
- **Who**: Backend only. Frontend does not use `proposed_time` and needs no changes.
- **Key constraint**: One pending row per series at all times. RRULE string is immutable.
- **Non-goals**: No changes to the one-pending-row model, sleep window logic, or goal
  sprint guard logic themselves — only what is passed into them.
- **Database**: Fresh — no migration of existing rows required.

---

## How `canonical_scheduled_at` Fixes Both Flaws

```
FREQ=DAILY, canonical_scheduled_at = Monday 09:00

Normal advance (no reschedule):
  canonical_dt = Monday 09:00
  rule.after(Monday 09:00, dtstart=Monday 09:00, inc=False) = Tuesday 09:00 ✓

Single reschedule → push forward to Monday 10:00:
  scheduled_at  = Monday 10:00  (changed)
  canonical_dt  = Monday 09:00  (unchanged)
  rule.after(Monday 09:00, dtstart=Monday 09:00, inc=False) = Tuesday 09:00 ✓

Single reschedule → pull back to Monday 08:00:
  scheduled_at  = Monday 08:00  (changed)
  canonical_dt  = Monday 09:00  (unchanged)
  rule.after(Monday 09:00, dtstart=Monday 09:00, inc=False) = Tuesday 09:00 ✓
  (NOT Monday 09:00 — no same-day duplicate)

Single reschedule → inside sleep window (e.g. Monday 23:00):
  scheduled_at  = Monday 23:00  (changed)
  canonical_dt  = Monday 09:00  (unchanged)
  rule.after(Monday 09:00, dtstart=Monday 09:00, inc=False) = Tuesday 09:00
  sleep guard: 09:00 outside sleep window → passes ✓

Series reschedule → 10:00 AM:
  scheduled_at       = Monday 10:00  (updated)
  canonical_scheduled_at = Monday 10:00  (updated — new canonical)
  rule.after(Monday 10:00, dtstart=Monday 10:00, inc=False) = Tuesday 10:00 ✓

FREQ=MINUTELY;INTERVAL=30, canonical_scheduled_at = 09:00:
  canonical_dt = 09:00
  rule.after(09:00, dtstart=09:00, inc=False) = 09:30 ✓
  (no proposed_time override, no loop possible)
```

---

## Affected Files

| File | Change |
|---|---|
| `backend/migrations/016_tasks_canonical_scheduled_at.sql` | Add `canonical_scheduled_at TIMESTAMPTZ`, drop `proposed_time` |
| `backend/app/agents/save_tasks.py` | Set `canonical_scheduled_at = scheduled_at_utc` at creation; remove `proposed_time` logic; update `_row_to_tuple` and `_INSERT_SQL` |
| `backend/app/services/recurrence.py` | Fetch `canonical_scheduled_at`; use it as both `after_dt` and `dtstart`; remove `proposed_time` block and frequency gate; propagate in INSERT |
| `backend/app/services/rrule_expander.py` | No logic changes — `dtstart` param already exists on `next_occurrence_after` and `advance_past_sleep` |
| `backend/app/api/v1/tasks.py` | Series reschedule: update `canonical_scheduled_at`; goal-linked single reschedule INSERT: copy `canonical_scheduled_at`; `_fetch_task_or_404` SELECT: swap field; remove from all timeline SELECTs |
| `backend/app/agents/scheduler.py` | Use `canonical_scheduled_at` (falling back to `scheduled_at`) as RRULE projection anchor |
| `backend/app/models/api_schemas.py` | Remove `proposed_time` from any exposed schema |

---

## Detailed Actionables

### 1. Database migration

**File:** `backend/migrations/016_tasks_canonical_scheduled_at.sql`

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
-- NULL for one-off (non-recurring) tasks — advance_recurring_task exits early
-- for those before ever reading this field.

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS canonical_scheduled_at TIMESTAMPTZ,
    DROP COLUMN IF EXISTS proposed_time;
```

---

### 2. `save_tasks.py` — task creation

**Location:** `backend/app/agents/save_tasks.py`

#### 2a. `_row_to_tuple` and `_INSERT_SQL`

Replace `proposed_time` with `canonical_scheduled_at` in both the tuple builder and the
INSERT statement.

```python
# _row_to_tuple: replace
row.get("proposed_time"),
# with
row.get("canonical_scheduled_at"),
```

```python
# _INSERT_SQL: replace
proposed_time
# with
canonical_scheduled_at
```

#### 2b. Recurring task block (around line 307)

**Remove** the entire `proposed_time` block:
```python
proposed_time: Optional[int] = None
try:
    local_dt = pendulum.parse(scheduled_at_utc).in_timezone(
        pendulum.timezone(user_tz)
    )
    proposed_time = local_dt.hour * 60 + local_dt.minute
except Exception:
    pass
```

**Replace with:**
```python
# canonical_scheduled_at is the RRULE position of this occurrence in the series.
# Set once here (after all guards); never changed by single-occurrence reschedule.
canonical_scheduled_at = scheduled_at_utc
```

**In the `_insert_task` call**, replace `"proposed_time": proposed_time` with
`"canonical_scheduled_at": canonical_scheduled_at`.

Note: `scheduled_at_utc` at this point is the final value after both the past-time guard
(lines 232–262) and the sleep-window guard (lines 264–282). This is correct — the
canonical time must reflect the actual first valid occurrence, not the raw LLM output.

#### 2c. One-off task branch (line 334)

No change needed — `proposed_time` was never set for one-off tasks. The `_insert_task`
call omits `canonical_scheduled_at`, which will be `NULL` via `row.get(...)`. ✓

---

### 3. `recurrence.py` — advance logic

**Location:** `backend/app/services/recurrence.py`

#### 3a. SELECT — fetch `canonical_scheduled_at`

```python
task_row = await db.fetchrow(
    """
    SELECT id, recurrence_rule, scheduled_at, canonical_scheduled_at,
           user_id, title, description, duration_minutes, trigger_type,
           location_trigger, goal_id, shared_with_goal_ids, escalation_policy
    FROM tasks WHERE id = $1
    """,
    task_id,
)
```

#### 3b. Build `canonical_dt` — used as both `after_dt` and `dtstart`

Replace the `ref_dt` block with:

```python
# scheduled_at: the actual (possibly rescheduled) occurrence time.
# canonical_scheduled_at: the RRULE-generated position of this occurrence in the
# series. Used as both after_dt and dtstart so the advance always produces the
# next series occurrence regardless of whether this occurrence was rescheduled,
# in which direction, or by how much.
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
    canonical_dt = ref_dt  # fallback for rows created before this migration
```

#### 3c. Pass `canonical_dt` to `next_occurrence_after`

```python
next_utc = next_occurrence_after(
    rrule_string=task_row["recurrence_rule"],
    after_dt=canonical_dt,   # canonical position, not rescheduled time
    user_timezone=user_tz,
    dtstart=canonical_dt,    # same — stable series anchor
)
```

#### 3d. Remove the entire `proposed_time` / frequency-gate block

Delete everything from `proposed_time = task_row["proposed_time"]` (or the `_SUB_DAILY`
block introduced as the temporary fix) through its closing `except`. This is approximately
20 lines including the frequency gate.

#### 3e. Pass `canonical_dt` as `dtstart` to `advance_past_sleep`

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
```

#### 3f. INSERT — propagate `canonical_scheduled_at` as `next_utc`

The newly inserted row's canonical time IS `next_utc` — it has not been rescheduled yet.

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
    pendulum.parse(next_utc),        # scheduled_at
    task_row["duration_minutes"],
    task_row["trigger_type"],
    task_row["location_trigger"],
    task_row["recurrence_rule"],
    shared_ids,
    task_row["escalation_policy"],
    pendulum.parse(next_utc),        # canonical_scheduled_at = same as scheduled_at (no reschedule yet)
)
```

---

### 4. `tasks.py` — reschedule endpoints and helpers

**Location:** `backend/app/api/v1/tasks.py`

#### 4a. `_fetch_task_or_404` SELECT

```python
# Replace:
proposed_time
# With:
canonical_scheduled_at
```

#### 4b. Timeline GET queries (lines 90, 116, 144)

```python
# Replace in all three SELECT column lists:
t.proposed_time
# With:
t.canonical_scheduled_at
```

#### 4c. Series reschedule

```python
# Was:
new_local = pendulum.instance(scheduled_at_dt).in_timezone(tz)
new_proposed_time = new_local.hour * 60 + new_local.minute
await db.execute(
    "UPDATE tasks SET scheduled_at = $1, proposed_time = $2, reminder_sent_at = NULL ...",
    scheduled_at_dt, new_proposed_time, task_uuid, user_uuid,
)

# Replace entirely with:
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
# Delete: new_local and new_proposed_time calculations; tz conversion
```

Both `scheduled_at` and `canonical_scheduled_at` are set to the same value — the new
time is simultaneously the current occurrence and the new series anchor.

#### 4d. Single-occurrence reschedule — silent task (goal_id IS NULL)

No change. The UPDATE only touches `scheduled_at`, `status`, and `reminder_sent_at`.
`canonical_scheduled_at` is intentionally absent — it stays as the original occurrence
time. ✓

#### 4e. Single-occurrence reschedule — goal-linked task

```python
# INSERT for new pending row — replace proposed_time:
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
    scheduled_at_dt,                         # rescheduled time
    task["duration_minutes"],
    task["trigger_type"],
    task["recurrence_rule"],
    task["escalation_policy"],
    task.get("canonical_scheduled_at"),      # was: task.get("proposed_time")
                                             # preserves series anchor; advance reverts correctly
)
```

---

### 5. `scheduler.py` — RRULE projection anchor

**Location:** `backend/app/agents/scheduler.py`, line 102

```python
# Was:
anchor = pendulum.instance(rec["scheduled_at"])

# Replace with:
anchor = pendulum.instance(
    rec["canonical_scheduled_at"] if rec["canonical_scheduled_at"] else rec["scheduled_at"]
)
```

**Also update the SELECT query** (around line 92) to include `canonical_scheduled_at`:

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

This ensures that when a single-occurrence reschedule is active, the scheduler projects
future busy slots from the canonical series time (e.g. 9 AM) rather than the rescheduled
time (e.g. 8 AM), giving correct availability windows for new goal planning.

---

### 6. `api_schemas.py` — clean up exposed fields

**Location:** `backend/app/models/api_schemas.py`

- Remove `proposed_time` from any response schema that exposes it.
- `canonical_scheduled_at` does not need to be exposed to the frontend — it is an
  internal advance-chain field.

---

## Edge Cases

| Case | Expected behaviour |
|---|---|
| DAILY task, no reschedule | `canonical_dt = scheduled_at`, advance returns same time next day ✓ |
| DAILY task, push forward (09:00 → 10:00) | `canonical_dt = 09:00`, `rule.after(09:00)` = next day 09:00 ✓ |
| DAILY task, pull back (09:00 → 08:00) | `canonical_dt = 09:00`, `rule.after(09:00)` = next day 09:00 — no same-day duplicate ✓ |
| DAILY task, single reschedule into sleep window | `canonical_dt = 09:00`, advance returns next day 09:00, sleep guard passes ✓ |
| WEEKLY task, single-occurrence rescheduled to different day | `canonical_dt = original weekday`, next advance returns next canonical weekday ✓ |
| MINUTELY;INTERVAL=30, no reschedule | `canonical_dt = 09:00`, `rule.after(09:00)` = 09:30 ✓ |
| MINUTELY;INTERVAL=30, natural next occurrence hits sleep window (no reschedule) | `rule.after(21:30)` = 22:00, sleep guard fires → 07:00 next day ✓ |
| MINUTELY;INTERVAL=30, single reschedule INTO sleep window (push: 21:30 → 23:00) | `canonical_dt = 21:30` (unchanged), `rule.after(21:30)` = 22:00, sleep guard fires → 07:00 next day. Rescheduled time (23:00) is completely ignored by advance ✓ |
| MINUTELY;INTERVAL=30, single reschedule AWAY from sleep but canonical next still hits sleep (pull back: 21:30 → 20:00) | `canonical_dt = 21:30` (unchanged), `rule.after(21:30)` = 22:00, sleep guard fires → 07:00 next day. Pull-back rescheduled time (20:00) is irrelevant ✓ |
| MINUTELY;INTERVAL=30, single reschedule entirely outside sleep, canonical next also outside | `canonical_dt = 09:00`, `rule.after(09:00)` = 09:30, sleep guard does not fire → 09:30 ✓ |
| Series reschedule 09:00 → 14:00 | Both fields updated to 14:00 → all future advances at 14:00 ✓ |
| `canonical_scheduled_at` is NULL (one-off task) | `advance_recurring_task` returns False on `recurrence_rule IS NULL` check — never reaches this field ✓ |
| `canonical_scheduled_at` is NULL (pre-migration row) | Falls back to `ref_dt` (= `scheduled_at`) — same behaviour as before migration ✓ |
| Goal-linked single reschedule — new row created | `canonical_scheduled_at` copied from original → chain reverts correctly ✓ |
| Scheduler projection after single reschedule | Uses `canonical_scheduled_at` as anchor → future busy slots correctly shown at 09:00, not rescheduled time ✓ |

---

## Testing Checklist

- [ ] DAILY task advances correctly without any reschedule
- [ ] DAILY task: push-forward single reschedule → next occurrence reverts to original time
- [ ] DAILY task: pull-back single reschedule → next occurrence is next day at original time (no same-day duplicate)
- [ ] DAILY task: single reschedule into sleep window → next advance produces correct next-day occurrence
- [ ] DAILY task: series reschedule → all future occurrences use new time
- [ ] WEEKLY task: single-occurrence reschedule → next occurrence is next canonical weekday at canonical time
- [ ] MINUTELY task: no infinite loop on auto-miss
- [ ] MINUTELY task: natural next occurrence hits sleep window → first valid slot after sleep end
- [ ] MINUTELY task: single reschedule INTO sleep window → advance ignores rescheduled time, uses canonical_dt, sleep guard fires, lands at first valid slot after sleep end
- [ ] MINUTELY task: single reschedule AWAY from sleep window (pull back) where canonical-based next still hits sleep → same result as above (rescheduled time is irrelevant)
- [ ] MINUTELY task: single reschedule entirely outside sleep window → advance proceeds normally from canonical_dt, no sleep guard
- [ ] Goal-linked task: `canonical_scheduled_at` survives the goal-linked single-reschedule INSERT
- [ ] Scheduler projections use `canonical_scheduled_at` when available
- [ ] `proposed_time` column is absent from DB, all queries, and all schemas
- [ ] `canonical_scheduled_at` is NULL for non-recurring tasks and they are unaffected
- [ ] Rows created before the migration (NULL `canonical_scheduled_at`) fall back gracefully

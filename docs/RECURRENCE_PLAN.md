# Recurrence & Date Navigation Plan

Three self-contained features. Implement in order — each is independent but C depends on B being done first in spirit (B proves auto-miss works; C handles the gap auto-miss leaves for future dates).

---

## Feature A — Date Navigation Cap (±6 weeks)

**Scope:** Frontend only. No backend changes.

**File:** `frontend/src/components/flow/v2/DateHeader.tsx`

### Changes

1. Compute `minDate` and `maxDate` once inside the component:
   ```
   minDate = today - 42 days  (YYYY-MM-DD string)
   maxDate = today + 42 days  (YYYY-MM-DD string)
   ```

2. Clamp `go(offsetDays)` so the computed next date never goes below `minDate` or above `maxDate`. If already at the bound, call should be a no-op.

3. Disable the `<ChevronLeft>` button when `activeDate === minDate`. Disable `<ChevronRight>` when `activeDate === maxDate`.

4. Add `min={minDate}` and `max={maxDate}` to the hidden `<input type="date">` so the native date picker is also bounded.

---

## Feature B — Bulletproof Auto-Miss

**Scope:** Backend only. No frontend changes.

### Files changed

| File | Change |
|---|---|
| `backend/app/config.py` | Add `auto_miss_grace_minutes: int = 90` |
| `backend/.env.example` | Add `AUTO_MISS_GRACE_MINUTES=90` |
| `backend/notifier/poll.py` | Rewrite `_step_auto_miss` |

### `_step_auto_miss` — new logic

Replace the three policy-dependent sub-queries with a single time-based query:

```sql
SELECT id, user_id FROM tasks
WHERE status = 'pending'
  AND trigger_type = 'time'
  AND scheduled_at IS NOT NULL
  AND scheduled_at <= now() - ('{grace} minutes')::interval
```

where `grace = settings.auto_miss_grace_minutes`.

- `_process_auto_miss` is **unchanged** — it still marks missed + calls `advance_recurring_task`.
- The notification steps (`_step_push`, `_step_whatsapp`, `_step_call`) are **unchanged** — they continue to fire independently; they are now purely informational, no longer gates for auto-miss.

### Why this works

| Scenario | Before | After |
|---|---|---|
| No push subscription | Tasks stuck as `pending` forever | Auto-missed after grace period ✓ |
| Push sent, user ignored | Auto-missed (already worked) | Same ✓ |
| User acted in app | `status ≠ 'pending'` — excluded | Same ✓ |
| Notifier was down | Backlog never cleared | Catches up all overdue on next poll ✓ |
| Location-triggered tasks | Excluded by notification chain | Excluded by `trigger_type = 'time'` ✓ |

### Grace period calibration

`auto_miss_grace_minutes` should be at least as long as the longest notification chain to give push/WhatsApp/call time to fire before auto-miss kicks in. Default `90` covers `escalation_window_minutes (2) × 3 channels × some buffer`.

---

## Feature C — RRULE Projection for Future Dates (Solution A)

**Scope:** Backend API + Frontend. Fills the gap between the last auto-missed row and tomorrow (which auto-miss hasn't caught up to yet).

**Core rule:** Projection only activates for `target_date >= today`. Past dates are fully covered by real rows created by the notifier.

### Files changed

| File | Change |
|---|---|
| `backend/app/services/rrule_expander.py` | Add `occurrence_on_date()` helper |
| `backend/app/models/api_schemas.py` | Add `TaskActionRequest` schema |
| `backend/app/api/v1/tasks.py` | Overlay projections in `GET /tasks`; accept `occurrence_date` in complete/missed |
| `frontend/src/services/TasksService.ts` | Add optional `occurrenceDate` param to `completeTask` / `missedTask` |
| `frontend/src/routes/index.tsx` | Thread `occurrenceDate` through `mapTaskToDisplayTypes` → `handleComplete` / `handleMissed` |

---

### C.1 — New helper: `occurrence_on_date`

**File:** `backend/app/services/rrule_expander.py`

```python
def occurrence_on_date(
    rrule_string: str,
    task_scheduled_at: pendulum.DateTime,   # current pending row's scheduled_at (UTC)
    target_date: str,                        # YYYY-MM-DD in user's local timezone
    user_timezone: str,
) -> str | None:
    """
    Return the UTC ISO8601 time of the occurrence on target_date if the
    RRULE (anchored at task_scheduled_at) has one, else None.
    """
```

Implementation:
- Convert `task_scheduled_at` to user's local timezone → use as `dtstart` (naive)
- Parse `target_date` as `start_of_day` and `end_of_day` in user's local timezone
- `rule.between(start_of_day_naive, end_of_day_naive, inc=True)` → returns 0 or 1 occurrences
- If 1 occurrence found, localise + convert to UTC ISO8601 and return
- `dtstart` being the pending row's `scheduled_at` means dates before task creation return `None` automatically

---

### C.2 — New schema: `TaskActionRequest`

**File:** `backend/app/models/api_schemas.py`

```python
class TaskActionRequest(BaseModel):
    occurrence_date: Optional[str] = None  # YYYY-MM-DD; only for projected occurrences
```

---

### C.3 — Modified: `GET /tasks`

**File:** `backend/app/api/v1/tasks.py`

After the existing `scheduled_rows` query, add a projection step **only when `target_date >= today`**:

1. Fetch all `pending` recurring tasks for this user:
   ```sql
   SELECT ... FROM tasks
   WHERE user_id = $1
     AND status = 'pending'
     AND recurrence_rule IS NOT NULL
     AND scheduled_at IS NOT NULL
   ```

2. Build a set of IDs already present in `scheduled_rows` to avoid double-counting the pending task when it falls on today.

3. For each recurring task **not already in `scheduled_rows`**:
   - Call `occurrence_on_date(task.recurrence_rule, task.scheduled_at, target_date, user_tz)`
   - If an occurrence is found, synthesize a projection dict:
     ```python
     {
         **task_fields,              # all real fields from the DB row
         "scheduled_at": occurrence_utc_iso,   # overridden to this day's time
         "is_projected": True,
         "occurrence_date": target_date,
     }
     ```

4. Append projections to the result, sorted by `scheduled_at`.

**Result:** The response shape gains two optional fields: `is_projected: bool` and `occurrence_date: str`. Non-projected tasks do not include these fields (or they are `false`/`null`).

---

### C.4 — Modified: `PATCH /{task_id}/complete` and `/missed`

**File:** `backend/app/api/v1/tasks.py`

Both endpoints gain an optional request body:

```python
body: TaskActionRequest = Body(default_factory=TaskActionRequest)
```

When `body.occurrence_date` is provided **and** `task.scheduled_at.date() != occurrence_date`:

1. Compute the occurrence time: `occurrence_on_date(task.recurrence_rule, task.scheduled_at, body.occurrence_date, user_tz)`
2. `UPDATE tasks SET scheduled_at = <occurrence_utc> WHERE id = $1` — materialize the occurrence in-place before advancing
3. Continue with the normal done/missed + `advance_recurring_task` flow

This ensures `advance_recurring_task` always advances from the occurrence the user actually acted on, not the original stale `scheduled_at`.

No change needed to `advance_recurring_task` itself.

---

### C.5 — Modified: `TasksService.ts`

**File:** `frontend/src/services/TasksService.ts`

```typescript
completeTask(taskId: string, occurrenceDate?: string): Promise<...>
missedTask(taskId: string, occurrenceDate?: string): Promise<...>
```

When `occurrenceDate` is provided, send it in the PATCH body:
```json
{ "occurrence_date": "2026-03-15" }
```

---

### C.6 — Modified: `index.tsx`

**File:** `frontend/src/routes/index.tsx`

Three touch points:

1. **`mapTaskToDisplayTypes`** — extract `is_projected` and `occurrence_date` from the raw task and pass them through to `TimelineEvent` (add `isProjected?: boolean` and `occurrenceDate?: string` to the `TimelineEvent` type in `types/event.ts`).

2. **`handleComplete(taskId)`** — change signature to `handleComplete(taskId: string, occurrenceDate?: string)`. Pass `occurrenceDate` to `tasksService.completeTask`.

3. **`handleMissed(taskId)`** (and the `missed_task_id` search param handler if it exists) — same pattern.

The `FlowTimeline` component must forward `occurrenceDate` down to wherever the complete/missed callbacks are invoked. This may require a small prop addition to `FlowTimeline` and its task item children.

---

## Rollout order

```
A  →  B  →  C.1  →  C.2  →  C.3  →  C.4  →  C.5  →  C.6
```

A and B can be done in parallel. C must follow B (conceptually) and its sub-steps are sequential.

## No DB migrations required

All changes are logic-only. No new columns, no new tables.

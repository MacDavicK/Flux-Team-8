# Congestion-Aware Start Date Suggestion — Design Spec

**Date:** 2026-03-21
**Status:** Approved

---

## Goal

When a user approves a goal plan and is asked when to start, Flux should proactively suggest the lightest available day and disable visually congested dates in the calendar picker — so the user never accidentally picks a day that cannot fit any of their new tasks.

---

## Background

The `ask_start_date_node` fires after goal approval and before the scheduler fan-out. At that point `goal_draft.plan.proposed_tasks` is already in state (with `duration_minutes` per task), so the minimum task duration for the new plan is knowable. The scheduler runs *after* the user picks a date, anchored to `goal_start_date`.

---

## Congestion Formula

A calendar day is **congested** when there is not enough free time to fit even the smallest new task:

```
sleep_minutes  = minutes from sleep_window.start to sleep_window.end (mod 24 h)
work_minutes   = work_minutes_by_day[weekday]   (480 Mon–Fri / 0 Sat–Sun if key absent)
task_minutes   = Σ duration_minutes of existing materialized tasks on that date
               + Σ duration_minutes of projected recurring task occurrences on that date
free_minutes   = 24×60 − sleep_minutes − work_minutes − task_minutes

congested  ⟺  free_minutes ≤ min(new_plan_task_durations)
```

**Known limitation:** if sleep and work hours overlap (e.g. graveyard shift), the formula double-counts those minutes. Accepted as a rare edge case for a heuristic check.

**Recurring task projections:** `ask_start_date_node` calls `projected_occurrences_in_window` (from `rrule_expander.py`) for each pending recurring task to include virtual future occurrences in the task_minutes sum. Without this, a user with daily recurring tasks would appear artificially free on all days beyond the first materialized row.

---

## Architecture

### New files

| File | Responsibility |
|---|---|
| `backend/app/services/congestion.py` | Pure `compute_free_minutes(profile, task_durations_on_day, date)` function. No DB calls. |

### Modified files

| File | Change |
|---|---|
| `backend/app/agents/state.py` | Add `suggested_date: Optional[str]` and `congested_dates: Optional[list[str]]` to `AgentState`. |
| `backend/app/agents/onboarding.py` | Add `_parse_work_minutes_by_day()` LLM helper; call it in `_complete_onboarding`; merge result into `final_profile`. |
| `backend/app/agents/ask_start_date.py` | Pre-check next 14 days for congestion; write `suggested_date` and `congested_dates` into returned state dict. |
| `backend/app/models/api_schemas.py` | Add `suggested_date: Optional[str]` and `congested_dates: list[str] = []` to `ChatMessageResponse`. |
| `backend/app/api/v1/chat.py` | Extract `suggested_date` and `congested_dates` from final LangGraph state and pass to `ChatMessageResponse`. |
| `frontend/src/components/ui/CalendarPicker.tsx` | Add `disabledDates?: string[]` prop; apply to individual cells. |
| `frontend/src/components/chat/StartDatePicker.tsx` | Add `disabledDates?: string[]` and `defaultDate?: string` props; initialize selection from `defaultDate`. |
| `frontend/src/routes/chat.tsx` | Pass `suggested_date` → `defaultDate` and `congested_dates` → `disabledDates` to `StartDatePicker` on the new-message render path. |

---

## Data Model

### `users.profile` — two new fields

```json
{
  "sleep_window": { "start": "23:00", "end": "07:00" },
  "work_minutes_by_day": {
    "mon": 540, "tue": 420, "wed": 540,
    "thu": 480, "fri": 180, "sat": 0, "sun": 0
  }
}
```

`sleep_window` already exists (structured at onboarding via quick-select + `_parse_time_to_24h`). No change needed there.

`work_minutes_by_day` is new — parsed from the existing natural-language `work_hours` string by a single LLM call at the end of onboarding. Stored alongside `work_hours` (raw string retained for display purposes).

**Fallback if parse fails:**
```json
{ "mon": 480, "tue": 480, "wed": 480, "thu": 480, "fri": 480, "sat": 0, "sun": 0 }
```

Special cases the LLM handles naturally:
- `"I don't work set hours"` → all zeros
- `"Flexible hours, mostly weekdays"` → moderate estimate (e.g. 360 min Mon–Fri)
- Irregular schedules (e.g. `"Mon–Wed 9–6, Tue 10–5, Thu 12–8, Fri 11–2"`) → per-day values

No DB schema change — both fields live in the existing `users.profile JSONB` column.

### Existing users (pre-feature)

`work_minutes_by_day` is absent for users who completed onboarding before this feature ships. Strategy: **lazy-fill in `ask_start_date_node`**. On first invocation, if `profile.get("work_minutes_by_day")` is `None`, call `_parse_work_minutes_by_day(profile.get("work_hours", ""))` and persist the result to `users.profile` before running the congestion check. This ensures existing users get the feature on their next goal without a separate migration job.

---

## Component Design

### `congestion.py` — pure service

```python
_WORK_FALLBACK = {
    "mon": 480, "tue": 480, "wed": 480, "thu": 480, "fri": 480, "sat": 0, "sun": 0
}

def compute_free_minutes(
    profile: dict,
    task_duration_minutes_on_day: list[int],
    date: datetime.date,
) -> int:
    """
    Returns estimated free minutes on `date` given the user's profile
    and the durations of existing tasks already scheduled that day
    (both materialized and projected recurring occurrences).

    Pure function — no DB calls, no side effects.
    """
```

- `sleep_minutes`: computed from `profile["sleep_window"]` using `parse_sleep_window` from `rrule_expander.py` (handles midnight wrap-around). Falls back to 480 min if key absent.
- `work_minutes`: `profile.get("work_minutes_by_day", _WORK_FALLBACK).get(weekday_abbr, 0)` where `weekday_abbr = date.strftime("%a").lower()`
- `task_minutes`: `sum(task_duration_minutes_on_day)`
- Returns `max(0, 24*60 - sleep_minutes - work_minutes - task_minutes)`

The internal `_WORK_FALLBACK` dict ensures the fallback (480 min Mon–Fri) is applied inside `compute_free_minutes` itself — not just at onboarding time — so pre-feature users get a sensible estimate even before lazy-fill runs.

---

### `state.py` — `AgentState` additions

```python
suggested_date: Optional[str]          # YYYY-MM-DD; set by ask_start_date_node
congested_dates: Optional[list[str]]   # YYYY-MM-DD list; set by ask_start_date_node
```

Both use the default `None` value (no custom reducer needed — only `ask_start_date_node` writes them, no fan-out merging required).

---

### `onboarding.py` — `_parse_work_minutes_by_day`

```python
async def _parse_work_minutes_by_day(work_hours: str) -> dict[str, int]:
    """
    One structured LLM call that converts a natural-language work schedule
    string into a per-day-of-week minute map.

    Called once in _complete_onboarding (and lazily in ask_start_date_node
    for pre-feature users). Never raises — returns fallback on error.
    """
```

- Uses `validated_llm_call` from `app/services/llm.py` (consistent with existing agent pattern)
- Model: `openrouter/openai/gpt-4o-mini`
- Pydantic output schema:
  ```python
  class WorkMinutesByDay(BaseModel):
      mon: int; tue: int; wed: int; thu: int; fri: int; sat: int; sun: int
  ```
- Fallback on any exception: `{"mon": 480, "tue": 480, "wed": 480, "thu": 480, "fri": 480, "sat": 0, "sun": 0}`
- Called inside `_complete_onboarding`, result merged into `final_profile` before the DB write

---

### `ask_start_date.py` — congestion pre-check

**Added logic before the question is generated:**

1. **Lazy-fill** `work_minutes_by_day` if absent: call `_parse_work_minutes_by_day` and write result to `users.profile` immediately.

2. Read `min_task_duration = min(t["duration_minutes"] for t in goal_draft["plan"]["proposed_tasks"])`. Default to 30 if plan is absent or empty.

3. Fetch materialized tasks for the next 14 days:
   ```sql
   SELECT scheduled_at, duration_minutes
   FROM tasks
   WHERE user_id = $1
     AND status IN ('pending', 'rescheduled')
     AND scheduled_at >= $2
     AND scheduled_at < $3
   ```

4. Fetch pending recurring tasks and expand via `projected_occurrences_in_window` into the same 14-day window. Merge with materialized tasks, deduplicating by (title, scheduled_at).

5. Group all task durations by local date (using `user_tz`). For each of the next 14 days, call `compute_free_minutes(profile, durations_on_day, date)`.

6. Build:
   - `congested_dates: list[str]` — YYYY-MM-DD strings where `free_minutes <= min_task_duration`
   - `suggested_date: str | None` — date with maximum `free_minutes` among non-congested days in the window; `None` if all 14 days are congested

7. Question text:
   - If `suggested_date` is set: `"Your schedule looks lightest on {formatted_date}. Want to start then, or pick another date?"`
   - Fallback (all congested or no profile data): `"When would you like to start?"`

8. Return `suggested_date` and `congested_dates` in the state dict. When all 14 days are congested, still return all 14 dates in `congested_dates` (calendar disables them) — the user can navigate to future months and pick a date beyond the window.

---

### `chat.py` — `send_message` handler

In the `ChatMessageResponse(...)` construction (currently lines ~446–456), add:

```python
resp = ChatMessageResponse(
    conversation_id=conversation_id,
    message=reply,
    agent_node=agent_node_value,
    proposed_plan=goal_draft if approval_pending else None,
    # ... existing fields ...
    rag_used=_rag_used,
    rag_sources=_rag_sources,
    suggested_date=result.get("suggested_date"),          # NEW
    congested_dates=result.get("congested_dates") or [],  # NEW
)
```

Also add `chat.py` to imports: `suggested_date` and `congested_dates` are plain `Optional[str]` / `list[str]` — no additional imports needed.

---

### API schema — `ChatMessageResponse`

```python
class ChatMessageResponse(BaseModel):
    # ... existing fields ...
    suggested_date: Optional[str] = None   # YYYY-MM-DD; set when ask_start_date fires
    congested_dates: list[str] = []        # YYYY-MM-DD list; empty when not applicable
```

---

### Frontend — `CalendarPicker.tsx`

Add prop:
```ts
disabledDates?: string[]   // YYYY-MM-DD strings; these cells render as unselectable
```

In cell render: `const isCongested = disabledDates?.includes(toISODate(day)) ?? false`

Fold into `isDisabled`. Congested cells use the same muted style as past/out-of-range cells (`text-river/25 cursor-not-allowed`). Optionally add a subtle dot indicator to distinguish congested from past — decision left to implementation.

---

### Frontend — `StartDatePicker.tsx`

Add props:
```ts
disabledDates?: string[]
defaultDate?: string       // YYYY-MM-DD; pre-selects this date instead of today
```

- Initialize `selected` state from `defaultDate ?? todayStr`
- Forward `disabledDates` to `CalendarPicker`

---

### Frontend — `chat.tsx`

On the **new-message render path** (where `StartDatePicker` is rendered for the current live turn), pass:
```tsx
<StartDatePicker
  defaultDate={message.suggested_date ?? undefined}
  disabledDates={message.congested_dates ?? []}
  onSelect={handleStartDateSelect}
/>
```

**History-replay path:** When loading prior conversation history, `suggested_date` and `congested_dates` are not persisted in `messages.metadata` and will not be available. The `StartDatePicker` on the history-replay path defaults to today with no disabled dates — this is acceptable because the user has already submitted a start date by the time they view history. No change needed on the history-replay render site.

---

## Data Flow

```
Onboarding completes
  → _complete_onboarding calls _parse_work_minutes_by_day(work_hours)
  → work_minutes_by_day merged into final_profile
  → written to users.profile

Goal approved
  → ask_start_date_node fires
  → lazy-fill work_minutes_by_day if absent (pre-feature users)
  → reads min_task_duration from goal_draft.plan.proposed_tasks
  → fetches materialized + projected recurring tasks for next 14 days
  → calls compute_free_minutes() per day
  → builds congested_dates + suggested_date
  → sets question text (with or without suggestion)
  → writes suggested_date + congested_dates into returned state dict

API layer (send_message handler in chat.py)
  → reads result.get("suggested_date") and result.get("congested_dates")
  → passes to ChatMessageResponse(suggested_date=..., congested_dates=...)

Frontend
  → StartDatePicker receives defaultDate + disabledDates
  → CalendarPicker pre-selects suggested_date, disables congested_dates
  → user picks date → sent as normal START_DATE message
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `work_minutes_by_day` absent from profile (pre-feature users) | Lazy-fill via `_parse_work_minutes_by_day`; falls back to 480 min Mon–Fri inside `compute_free_minutes` if still absent |
| LLM parse of `work_hours` fails (onboarding or lazy-fill) | Fallback dict used; never blocks flow |
| All 14 days are congested | `suggested_date = None`; neutral question shown; all 14 dates still included in `congested_dates` so calendar disables them; user navigates to future months |
| `goal_draft.plan` absent or empty | `min_task_duration` defaults to 30 min; congestion check still runs |
| DB query for existing tasks fails | Log warning; `congested_dates = []`, `suggested_date = None`; question falls back to neutral |

---

## Testing

- **Unit:** `compute_free_minutes` — standard day, congested day, midnight-wrap sleep window, absent `work_minutes_by_day` uses fallback (not zero)
- **Unit:** `_parse_work_minutes_by_day` — mock `validated_llm_call`; standard schedule, irregular schedule, "I don't work set hours", LLM failure → fallback
- **Unit:** `ask_start_date_node` — mock DB + profile; verify `congested_dates` and `suggested_date` in returned state; verify recurring task projections are included in task_minutes
- **Unit:** lazy-fill path — absent `work_minutes_by_day` triggers parse + DB write before congestion check
- **Integration:** Full onboarding → `work_minutes_by_day` present in saved profile
- **Frontend:** `CalendarPicker` with `disabledDates` — congested cells are unclickable; `StartDatePicker` initialises to `defaultDate`

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
work_minutes   = work_minutes_by_day[weekday]   (0 if key absent)
task_minutes   = Σ duration_minutes of existing tasks on that date
free_minutes   = 24×60 − sleep_minutes − work_minutes − task_minutes

congested  ⟺  free_minutes ≤ min(new_plan_task_durations)
```

**Known limitation:** if sleep and work hours overlap (e.g. graveyard shift), the formula double-counts those minutes. Accepted as a rare edge case for a heuristic check.

---

## Architecture

### New files

| File | Responsibility |
|---|---|
| `backend/app/services/congestion.py` | Pure `compute_free_minutes(profile, task_durations_on_day, date)` function. No DB calls. |

### Modified files

| File | Change |
|---|---|
| `backend/app/agents/onboarding.py` | Add `_parse_work_minutes_by_day()` LLM helper; call it in `_complete_onboarding`; merge result into `final_profile`. |
| `backend/app/agents/ask_start_date.py` | Pre-check next 14 days for congestion; include `suggested_date` and `congested_dates` in state for the API layer to surface. |
| `backend/app/models/api_schemas.py` | Add `suggested_date: Optional[str]` and `congested_dates: list[str] = []` to `ChatMessageResponse`. |
| `frontend/src/components/ui/CalendarPicker.tsx` | Add `disabledDates?: string[]` prop; apply to individual cells. |
| `frontend/src/components/chat/StartDatePicker.tsx` | Add `disabledDates?: string[]` and `defaultDate?: string` props; initialize selection from `defaultDate`. |
| `frontend/src/routes/chat.tsx` | Pass `suggested_date` → `defaultDate` and `congested_dates` → `disabledDates` to `StartDatePicker`. |

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

---

## Component Design

### `congestion.py` — pure service

```python
def compute_free_minutes(
    profile: dict,
    task_duration_minutes_on_day: list[int],
    date: datetime.date,
) -> int:
    """
    Returns estimated free minutes on `date` given the user's profile
    and the durations of existing tasks already scheduled that day.

    Pure function — no DB calls, no side effects.
    """
```

- `sleep_minutes`: computed from `profile["sleep_window"]` (handles midnight wrap-around)
- `work_minutes`: `profile.get("work_minutes_by_day", {}).get(weekday_abbr, 0)`
  - `weekday_abbr` = `date.strftime("%a").lower()` → `"mon"`, `"tue"`, etc.
- `task_minutes`: `sum(task_duration_minutes_on_day)`
- Returns `max(0, 24*60 - sleep_minutes - work_minutes - task_minutes)`

---

### `onboarding.py` — `_parse_work_minutes_by_day`

```python
async def _parse_work_minutes_by_day(work_hours: str) -> dict[str, int]:
    """
    One structured LLM call (cheapest model) that converts a natural-language
    work schedule string into a per-day-of-week minute map.

    Called once in _complete_onboarding. Never raises — returns fallback on error.
    """
```

- Model: `gpt-4o-mini` (cheapest, sufficient for structured extraction)
- Output schema: `{"mon": int, "tue": int, "wed": int, "thu": int, "fri": int, "sat": int, "sun": int}`
- Fallback on any exception: `{"mon": 480, "tue": 480, "wed": 480, "thu": 480, "fri": 480, "sat": 0, "sun": 0}`
- Called inside `_complete_onboarding`, result merged into `final_profile` before the DB write

---

### `ask_start_date.py` — congestion pre-check

**Added logic before the question is generated:**

1. Read `min_task_duration = min(t["duration_minutes"] for t in goal_draft["plan"]["proposed_tasks"])`. Default to 30 if plan is absent or empty.

2. Fetch existing tasks for the next 14 days in a single DB query:
   ```sql
   SELECT scheduled_at, duration_minutes
   FROM tasks
   WHERE user_id = $1
     AND status IN ('pending', 'rescheduled')
     AND scheduled_at >= $2
     AND scheduled_at < $3
   ```

3. Group by local date (using `user_tz`). For each of the next 14 days, call `compute_free_minutes(profile, durations_on_day, date)`.

4. Build:
   - `congested_dates: list[str]` — YYYY-MM-DD strings where `free_minutes <= min_task_duration`
   - `suggested_date: str | None` — date with maximum `free_minutes` among non-congested days; `None` if all 14 days are congested

5. Question text:
   - If `suggested_date` is set: `"Your schedule looks lightest on {formatted_date}. Want to start then, or pick another date?"`
   - Fallback (all congested or no profile data): `"When would you like to start?"`

6. Return `suggested_date` and `congested_dates` in state so the API layer (`send_message` handler) can include them in `ChatMessageResponse`.

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

Fold into `isDisabled`. Congested cells use the same muted style as past/out-of-range cells (`text-river/25 cursor-not-allowed`). Optionally add a subtle visual marker (e.g. strikethrough or dot) to distinguish congested from simply past — decision left to implementation.

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

Where `StartDatePicker` is rendered for the start-date turn, pass:
```tsx
<StartDatePicker
  defaultDate={message.suggested_date ?? undefined}
  disabledDates={message.congested_dates ?? []}
  onSelect={handleStartDateSelect}
/>
```

---

## Data Flow

```
Onboarding completes
  → _complete_onboarding calls _parse_work_minutes_by_day(work_hours)
  → work_minutes_by_day merged into final_profile
  → written to users.profile

Goal approved
  → ask_start_date_node fires
  → reads min_task_duration from goal_draft.plan.proposed_tasks
  → fetches existing tasks for next 14 days (single DB query)
  → calls compute_free_minutes() per day
  → builds congested_dates + suggested_date
  → sets question text (with or without suggestion)
  → returns suggested_date + congested_dates in state

API layer (send_message handler)
  → reads suggested_date + congested_dates from final state
  → includes in ChatMessageResponse

Frontend
  → StartDatePicker receives defaultDate + disabledDates
  → CalendarPicker pre-selects suggested_date, disables congested_dates
  → user picks date → sent as normal START_DATE message
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `work_minutes_by_day` absent from profile (pre-feature users) | `compute_free_minutes` defaults to 480 min Mon–Fri via fallback dict |
| LLM parse of work_hours fails | Fallback dict written to profile; onboarding never blocks |
| All 14 days are congested | `suggested_date = None`; neutral question shown; no dates disabled |
| `goal_draft.plan` absent or empty | `min_task_duration` defaults to 30 min; congestion check still runs |
| DB query for existing tasks fails | Log warning; `congested_dates = []`, `suggested_date = None`; question falls back to neutral |

---

## Testing

- **Unit:** `compute_free_minutes` — test standard day, congested day, midnight-wrap sleep window, missing `work_minutes_by_day` key
- **Unit:** `_parse_work_minutes_by_day` — mock LLM call; test standard schedule, irregular schedule, "I don't work set hours", LLM failure → fallback
- **Unit:** `ask_start_date_node` — mock DB + profile; verify `congested_dates` and `suggested_date` in returned state
- **Integration:** Full onboarding → `work_minutes_by_day` present in saved profile
- **Frontend:** `CalendarPicker` with `disabledDates` — congested cells are unclickable; `StartDatePicker` initialises to `defaultDate`

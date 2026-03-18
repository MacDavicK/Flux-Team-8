# Plan: Fix Recurring Task Projection Blind Spot in Scheduler

## Context

When a user creates a goal with a future start date, the scheduler double-books slots already occupied by existing recurring tasks (e.g. "Evening Walk" and "German Pronunciation Practice" both land at 7:00 PM). The root cause is that recurring tasks are stored as a **single DB row** with an iCal RRULE — only the current/active occurrence is materialized. Future virtual occurrences are invisible to the scheduler's query.

**Three compounding bugs:**

| # | Bug | Location |
|---|-----|----------|
| 1 | Scheduler only queries materialized rows — `status IN ('pending', 'rescheduled')` misses all virtual future occurrences | `scheduler.py` lines 41–52 |
| 2 | Query window anchored to `now()` — when `goal_start_date = "next Monday"`, DB still queries `scheduled_at >= now()`, loading the wrong window | `scheduler.py` lines 41–52 |
| 3 | `goal_start_date` not passed in `Send()` slice — scheduler fan-out always sees `state.get("goal_start_date") == None` regardless of what was set | `graph.py` lines 172–180 |

**UX improvement (also implemented here):** Ask for the start date **before** generating the plan (pre-fan-out) rather than after approval. This gives the scheduler the correct date context from the first LLM run, eliminating the `reschedule` round-trip in the happy path.

---

## Current Flow (for reference)

```
GOAL message
  → orchestrator (sets intent="GOAL")
  → goal_clarifier (asks clarifying Qs if needed)
  → goal_planner fan-out                              ← scheduler runs here with now() window, no goal_start_date
      ├── classifier
      ├── scheduler  (Send slice has NO goal_start_date)
      └── pattern_observer
  → goal_planner (presents plan, waits for approval)
  → [user approves]
  → orchestrator (intent=APPROVE → approval_status="approved")
  → route_from_orchestrator: approved + proposed_tasks + NO goal_start_date → ask_start_date
  → ask_start_date (sets approval_status="awaiting_start_date", ends turn)
  → [user replies "next Monday"]
  → orchestrator (intent=START_DATE → approval_status="approved", goal_start_date="2026-03-23")
  → route_from_orchestrator: approved + proposed_tasks + goal_start_date → reschedule
  → reschedule (re-runs scheduler with goal_start_date, still missing projections)
  → save_tasks
```

## Target Flow (after this change)

```
GOAL message
  → orchestrator (sets intent="GOAL")
  → goal_clarifier (asks clarifying Qs if needed)
  → route_from_goal_clarifier: GOAL_PLAN + no goal_start_date → ask_start_date   ← MOVED HERE
  → ask_start_date (sets approval_status="awaiting_start_date", ends turn)
  → [user replies "next Monday"]
  → orchestrator (intent=START_DATE → approval_status="approved", goal_start_date="2026-03-23")
  → route_from_orchestrator: approved + NO proposed_tasks + goal_start_date → goal_planner
  → goal_planner fan-out                              ← scheduler runs here WITH goal_start_date + projections
      ├── classifier
      ├── scheduler  (Send slice NOW includes goal_start_date)
      └── pattern_observer
  → goal_planner (presents plan, waits for approval)
  → [user approves]
  → orchestrator (intent=APPROVE → approval_status="approved")
  → route_from_orchestrator: approved + proposed_tasks + goal_start_date → save_tasks   ← DIRECT, no reschedule
  → save_tasks
```

---

## Part 1 — Core Fix: RRULE Projection Enrichment

### Change 1 — Add `projected_occurrences_in_window()` to `rrule_expander.py`

**File:** `backend/app/services/rrule_expander.py`

**Where:** Add after the `occurrence_on_date()` function (~line 103), before `next_occurrence_after()`.

**Why a new function:** The existing `expand_rrule_to_tasks()` uses `start_dt` as both the RRULE `dtstart` anchor AND the `between()` lower bound. For conflict detection, the anchor is the task's wall-clock time from months ago, while the query window is a future date range. These must be separated.

```python
def projected_occurrences_in_window(
    rrule_string: str,
    task_scheduled_at: pendulum.DateTime,  # pending row's scheduled_at — RRULE dtstart anchor
    window_start: pendulum.DateTime,        # UTC lower bound of the planning window
    window_end: pendulum.DateTime,          # UTC upper bound of the planning window
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
```

---

### Change 2 — Rewrite the existing-tasks block in `scheduler_node`

**File:** `backend/app/agents/scheduler.py`

**Add import at the top of the file (after the existing imports):**

```python
from app.services.rrule_expander import projected_occurrences_in_window
```

**Replace lines 40–60 (the current materialized-only query block) with the following.** Also delete the now-duplicate `goal_start_date` assignment on original line 71 — it is moved to the top of this block.

```python
    # ── Compute planning window ────────────────────────────────────────────
    # Use goal_start_date (user's chosen start) as the window lower bound when
    # available. This fixes BUG #2: previously the window always started at
    # now() even when goal_start_date was set to next Monday.
    goal_start_date: str | None = state.get("goal_start_date")
    if goal_start_date:
        # Parse date-only string ("2026-03-23") in user's timezone so midnight
        # local time is the anchor, then convert to UTC.
        window_start = (
            pendulum.parse(goal_start_date, tz=pendulum.timezone(user_tz))
            .start_of("day")
            .in_timezone("UTC")
        )
    else:
        window_start = pendulum.now("UTC")
    window_end = window_start.add(weeks=6)

    # ── 1. Materialized tasks (real DB rows in the window) ─────────────────
    existing_rows = await db.fetch(
        """
        SELECT title, scheduled_at, duration_minutes
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND scheduled_at >= $2
          AND scheduled_at <= $3
        ORDER BY scheduled_at
        """,
        user_id,
        window_start,
        window_end,
    )
    existing_tasks_data: list[dict] = []
    seen: set[tuple[str, str]] = set()   # (title, scheduled_at ISO) dedup key
    for row in existing_rows:
        iso = row["scheduled_at"].isoformat()
        existing_tasks_data.append({
            "title": row["title"],
            "scheduled_at": iso,
            "duration_minutes": row["duration_minutes"],
            "is_projected": False,
        })
        seen.add((row["title"], iso))

    # ── 2. RRULE projections (virtual future occurrences of recurring tasks) ─
    # Fixes BUG #1: fetch ALL pending recurring tasks and expand their RRULE
    # into the planning window. These occurrences don't exist as DB rows yet
    # but are hard time blocks for the scheduler.
    recurring_rows = await db.fetch(
        """
        SELECT title, scheduled_at, duration_minutes, recurrence_rule
        FROM tasks
        WHERE user_id = $1
          AND status IN ('pending', 'rescheduled')
          AND recurrence_rule IS NOT NULL
        """,
        user_id,
    )
    for rec in recurring_rows:
        anchor = pendulum.instance(rec["scheduled_at"])
        for proj in projected_occurrences_in_window(
            rec["recurrence_rule"], anchor, window_start, window_end, user_tz
        ):
            key = (rec["title"], proj["scheduled_at"])
            if key in seen:
                continue  # already covered by the materialized query (same slot)
            existing_tasks_data.append({
                "title": rec["title"],
                "scheduled_at": proj["scheduled_at"],
                "duration_minutes": rec["duration_minutes"],
                "is_projected": True,
            })
            seen.add(key)

    # Sort merged list chronologically so the LLM receives a clean timeline.
    existing_tasks_data.sort(key=lambda x: x["scheduled_at"])
```

**Also remove the now-duplicate line** that originally appeared further down in the function:

```python
# DELETE this line (original line ~71) — goal_start_date is now set above:
goal_start_date: str | None = state.get("goal_start_date")
```

The `context_block` section that follows (builds the string passed to the LLM) uses `goal_start_date` which is now already set earlier in the function. No changes needed there.

---

### Change 3 — Update the scheduler prompt

**File:** `backend/app/agents/prompts/scheduler.txt`

**After the line** `- Never double-book existing tasks`, add:

```
- existing_tasks includes both real DB rows (is_projected: false) and projected
  virtual occurrences of recurring tasks (is_projected: true). Both are hard time
  blocks — never schedule new tasks overlapping either type.
```

---

## Part 2 — UX Fix: Ask Start Date Before the Fan-Out

### How the orchestrator handles START_DATE (no change needed here — for context)

**File:** `backend/app/agents/orchestrator.py` lines 107–118

```python
# APPROVE intent: user confirmed a pending plan
if result.intent == "APPROVE":
    return {"approval_status": "approved"}

# START_DATE intent: user replied to the start-date question.
if result.intent == "START_DATE":
    user_tz = profile.get("timezone", "UTC")
    goal_start_date = _parse_start_date(result.payload, messages, user_tz)
    return {
        "approval_status": "approved",
        "goal_start_date": goal_start_date,
    }
```

The orchestrator prompt (`orchestrator.txt` line 15) says:
> "START_DATE takes absolute priority: if approval_status == 'awaiting_start_date' (from context), ALWAYS use START_DATE"

`ask_start_date_node` sets `approval_status = "awaiting_start_date"` — this is the trigger. Since we're not changing `ask_start_date.py`, the prompt condition still applies correctly in the pre-fan-out position. **No changes needed to `orchestrator.py` or `orchestrator.txt`.**

**One addition needed in `orchestrator.py`:** The START_DATE return dict must also reset the sub-agent output fields. Without this, if an old session somehow has stale `classifier_output`/`scheduler_output`/`pattern_output`, `route_from_goal_planner` would skip the fan-out (it checks `if not (classifier_done and scheduler_done and pattern_done)`).

```python
# CURRENT (lines 112–118):
if result.intent == "START_DATE":
    user_tz = profile.get("timezone", "UTC")
    goal_start_date = _parse_start_date(result.payload, messages, user_tz)
    return {
        "approval_status": "approved",
        "goal_start_date": goal_start_date,
    }

# UPDATED:
if result.intent == "START_DATE":
    user_tz = profile.get("timezone", "UTC")
    goal_start_date = _parse_start_date(result.payload, messages, user_tz)
    return {
        "approval_status": "approved",
        "goal_start_date": goal_start_date,
        # Reset fan-out outputs so route_from_goal_planner triggers the fan-out
        # on the next call to goal_planner (pre-fan-out path).
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
    }
```

---

### Change 4 — `ask_start_date.py` — **no changes needed**

The node body is already correct. It appends the start-date question and sets `approval_status = "awaiting_start_date"`. Only the routing that invokes it changes.

```python
# ask_start_date.py — unchanged
async def ask_start_date_node(state: AgentState) -> dict:
    history = list(state.get("conversation_history") or [])
    question = (
        "When would you like to start? "
        'You can say "today", "tomorrow", "next Monday", or give me a specific date — '
        "and I'll schedule your first task from there."
    )
    return {
        "conversation_history": history + [{"role": "assistant", "content": question}],
        "approval_status": "awaiting_start_date",
    }
```

---

### Change 5 — Update `route_from_goal_clarifier` in `graph.py`

**File:** `backend/app/agents/graph.py` (~line 126)

```python
# CURRENT:
def route_from_goal_clarifier(state: AgentState) -> str:
    if state.get("intent") == "GOAL_PLAN":
        return "goal_planner"
    return END

# UPDATED:
def route_from_goal_clarifier(state: AgentState) -> str:
    if state.get("intent") == "GOAL_PLAN":
        # Ask for start date BEFORE the fan-out so the scheduler receives the
        # correct window on its first (and only) run. Skip if goal_start_date
        # is already in state (e.g. NEXT_MILESTONE re-entry; see edge cases).
        if not state.get("goal_start_date"):
            return "ask_start_date"
        return "goal_planner"
    return END
```

**LangGraph edge registration note:** `add_conditional_edges("goal_clarifier", route_from_goal_clarifier)` is already in `_build_graph()`. LangGraph resolves destinations at runtime from the function's return values. Since `ask_start_date` is already a registered node (`graph.add_node("ask_start_date", ask_start_date_node)`) and the existing `graph.add_edge("ask_start_date", END)` is present, **no new `add_edge` calls are needed** for this routing change.

---

### Change 6 — Update `route_from_orchestrator` in `graph.py`

**File:** `backend/app/agents/graph.py` (~line 78)

The key differentiator between pre-fan-out START_DATE (no plan yet) and post-approval APPROVE (plan already shown) is `proposed_tasks` — it is `None` before the plan is generated, and populated after `goal_planner` runs.

```python
# CURRENT (lines 78–118):
def route_from_orchestrator(state: AgentState) -> str:
    approval = state.get("approval_status") or ""

    if (
        approval == "approved"
        and state.get("proposed_tasks")
        and not state.get("goal_start_date")
    ):
        return "ask_start_date"

    if (
        approval == "approved"
        and state.get("proposed_tasks")
        and state.get("goal_start_date")
    ):
        return "reschedule"

    intent = state.get("intent") or ""

    if intent == "MODIFY_GOAL":
        goal_draft = state.get("goal_draft") or {}
        if not goal_draft.get("goal_id"):
            return "goal_planner"

    return {
        "ONBOARDING": "onboarding",
        "GOAL": "goal_clarifier",
        "GOAL_CLARIFY": "goal_clarifier",
        "NEW_TASK": "task_handler",
        "MODIFY_GOAL": "goal_modifier",
        "NEXT_MILESTONE": "goal_planner",
        "CHITCHAT": "chitchat",
        "CLARIFY": "clarify",
    }.get(intent, "chitchat")


# UPDATED:
def route_from_orchestrator(state: AgentState) -> str:
    approval = state.get("approval_status") or ""

    # Pre-fan-out: user answered the start-date question before any plan was
    # generated. proposed_tasks is None; goal_start_date was just set by the
    # orchestrator's START_DATE handler. Route to goal_planner to trigger the
    # fan-out with the correct date context.
    if (
        approval == "approved"
        and not state.get("proposed_tasks")
        and state.get("goal_start_date")
    ):
        return "goal_planner"

    # Post-approval: plan was presented and user approved. goal_start_date is
    # already set from the pre-fan-out question — go directly to save_tasks.
    # No reschedule needed: the fan-out scheduler already used goal_start_date.
    if (
        approval == "approved"
        and state.get("proposed_tasks")
        and state.get("goal_start_date")
    ):
        return "save_tasks"

    # Fallback: user approved but goal_start_date is missing (should not occur
    # in normal flow; guards against malformed session state).
    if (
        approval == "approved"
        and state.get("proposed_tasks")
        and not state.get("goal_start_date")
    ):
        return "ask_start_date"

    intent = state.get("intent") or ""

    if intent == "MODIFY_GOAL":
        goal_draft = state.get("goal_draft") or {}
        if not goal_draft.get("goal_id"):
            return "goal_planner"

    return {
        "ONBOARDING": "onboarding",
        "GOAL": "goal_clarifier",
        "GOAL_CLARIFY": "goal_clarifier",
        "NEW_TASK": "task_handler",
        "MODIFY_GOAL": "goal_modifier",
        "NEXT_MILESTONE": "goal_planner",
        "CHITCHAT": "chitchat",
        "CLARIFY": "clarify",
    }.get(intent, "chitchat")
```

---

### Change 7 — Update `route_from_goal_planner` in `graph.py`

**File:** `backend/app/agents/graph.py` (~line 137)

Two sub-changes:

**7a. Pass `goal_start_date` in the `Send()` slice for scheduler (fixes BUG #3).**

Find the `Send("scheduler", {...})` block inside `route_from_goal_planner` and add the field:

```python
# CURRENT (lines 172–180):
Send(
    "scheduler",
    {
        "user_id": user_id,
        "goal_draft": goal_draft,
        "user_profile": user_profile,
        "conversation_history": conv_history,
        "token_usage": token_usage,
    },
),

# UPDATED:
Send(
    "scheduler",
    {
        "user_id": user_id,
        "goal_draft": goal_draft,
        "user_profile": user_profile,
        "conversation_history": conv_history,
        "token_usage": token_usage,
        "goal_start_date": state.get("goal_start_date"),  # FIX BUG #3
    },
),
```

**7b. Simplify the post-approval block** (after all sub-agents have converged, ~line 194).

`goal_start_date` is always set by this point (collected pre-fan-out), so route directly to `save_tasks`:

```python
# CURRENT (lines 194–204):
approval = state.get("approval_status") or "negotiating"
if approval == "approved":
    if state.get("goal_start_date"):
        return "save_tasks"
    return "ask_start_date"
if approval == "abandoned":
    return END
return END

# UPDATED:
approval = state.get("approval_status") or "negotiating"
if approval == "approved":
    # goal_start_date is always set (asked pre-fan-out). Go directly to
    # save_tasks — no reschedule round-trip needed.
    return "save_tasks"
if approval == "abandoned":
    return END
return END
```

---

### Change 8 — `_build_graph()` edges: what changes, what stays

**File:** `backend/app/agents/graph.py` (~line 212)

| Edge | Status | Reason |
|------|--------|--------|
| `graph.add_edge("ask_start_date", END)` | **Keep unchanged** | Node still ends the turn in both pre-fan-out and fallback positions |
| `graph.add_edge("reschedule", "save_tasks")` | **Keep as dead code** | `reschedule` is no longer reachable from any routing function in the happy path. Removing it is optional — keep for now to avoid breaking any old in-flight sessions held in the LangGraph checkpointer |
| `graph.add_node("reschedule", scheduler_node)` | **Keep as dead code** | Same reason — in-flight session safety |
| No new edges needed | — | `goal_clarifier → ask_start_date` is inferred by LangGraph from `route_from_goal_clarifier`'s return values at runtime |

---

## State Fields Reference

All relevant fields already exist in `AgentState` (`backend/app/agents/state.py`). No schema changes needed.

| Field | Type | Set by | Used by |
|-------|------|--------|---------|
| `goal_start_date` | `Optional[str]` (ISO8601 date) | `orchestrator_node` on START_DATE intent | `scheduler_node`, `route_from_orchestrator`, `route_from_goal_clarifier`, `route_from_goal_planner` |
| `approval_status` | `Optional[str]` | `orchestrator_node` (APPROVE→`"approved"`), `ask_start_date_node` (`"awaiting_start_date"`) | `route_from_orchestrator`, `route_from_goal_planner` |
| `proposed_tasks` | `Optional[list[dict]]` | `goal_planner_node` after sub-agents converge | `route_from_orchestrator` — differentiates pre-fan-out vs post-approval |
| `classifier_output` | `Annotated[Optional[dict], _merge_dict]` | `classifier_node` | `route_from_goal_planner` (fan-out gate) |
| `scheduler_output` | `Annotated[Optional[dict], _merge_dict]` | `scheduler_node` | `route_from_goal_planner` (fan-out gate), `goal_planner_node` |
| `pattern_output` | `Annotated[Optional[dict], _merge_dict]` | `pattern_observer_node` | `route_from_goal_planner` (fan-out gate), `scheduler_node`, `goal_planner_node` |

**Minor doc fix (optional):** `state.py` line 44–46 lists `approval_status` values as `'pending' | 'approved' | 'approved_with_start' | 'negotiating' | 'abandoned'` but omits `'awaiting_start_date'`. Update the comment:

```python
# CURRENT:
approval_status: Optional[str]  # 'pending' | 'approved' | 'approved_with_start' | 'negotiating' | 'abandoned'

# UPDATED:
approval_status: Optional[str]  # 'pending' | 'approved' | 'awaiting_start_date' | 'negotiating' | 'abandoned'
```

---

## Edge Cases

| Scenario | What happens | Correct? |
|----------|-------------|----------|
| User includes date in the original GOAL message ("I want to run a 5K starting next Monday") | `orchestrator_node` processes intent=`GOAL`, does NOT parse dates in GOAL path — so `goal_start_date` is not set. `ask_start_date` fires after clarification. One extra round-trip. | Acceptable. Future optimisation: detect date in GOAL message in orchestrator. |
| User says "start today" or "now" | `_parse_start_date()` (orchestrator.py line 40–41) returns `now_local.to_date_string()`. `window_start = today midnight user-tz`. Identical behavior to pre-fix. | ✓ |
| User says "I'll decide later" / no parseable date | `_parse_start_date()` falls back to today (line 51). Scheduler uses today as window start. | ✓ |
| NEXT_MILESTONE intent | Routes `orchestrator → goal_planner` directly, bypassing `goal_clarifier`. `ask_start_date` does **not** fire (never reaches `route_from_goal_clarifier`). Scheduler defaults `window_start = now()`. | ✓ |
| MODIFY_GOAL on a draft (no goal_id) | Routes `orchestrator → goal_planner`, bypassing `goal_clarifier`. `goal_start_date` carries over from the original session. Scheduler uses it. | ✓ |
| Duplicate occurrence at window boundary | The `seen: set[tuple[str, str]]` keyed by `(title, scheduled_at ISO)` deduplicates. Materialized row wins (added first). | ✓ |
| Old in-flight session in LangGraph checkpointer (pre-change) | `proposed_tasks` is set and `goal_start_date` may or may not be set. `route_from_orchestrator` fallback `ask_start_date` handles the no-date case; `save_tasks` handles the has-date case. | ✓ |

---

## Files Modified — Complete List

| File | Change summary |
|------|---------------|
| `backend/app/services/rrule_expander.py` | Add `projected_occurrences_in_window()` after `occurrence_on_date()` |
| `backend/app/agents/scheduler.py` | Add import; replace lines 40–60 with window computation + materialized query + RRULE projection block; remove duplicate `goal_start_date` assignment (~line 71) |
| `backend/app/agents/prompts/scheduler.txt` | Add 3 lines after "Never double-book existing tasks" explaining `is_projected` |
| `backend/app/agents/orchestrator.py` | Add `classifier_output/scheduler_output/pattern_output: None` reset to START_DATE return dict (lines 112–118) |
| `backend/app/agents/graph.py` | 4 sub-changes: `route_from_goal_clarifier`, `route_from_orchestrator`, `route_from_goal_planner` approval block, `Send()` slice for scheduler |
| `backend/app/agents/ask_start_date.py` | **No change** |
| `backend/app/agents/state.py` | Minor doc fix: add `'awaiting_start_date'` to `approval_status` comment |

---

## Verification

### Test 1 — Projection coverage (core bug)
1. Create a recurring task: "Daily Standup, `FREQ=DAILY` at 09:00" with `scheduled_at` = today, `status = 'pending'`.
2. Start a new goal: "I want to learn piano."
3. When asked for start date, reply "next Monday."
4. Check the LLM call context logged in LangSmith / stdout — `existing_tasks_data` passed to the scheduler must contain approximately 42 "Daily Standup" entries (6 weeks × 7 days) with `is_projected: true`, starting from next Monday.
5. Verify the scheduler does not assign any piano task at 09:00.

### Test 2 — Query window anchor
1. Same setup. Add a `logger.debug(f"window_start={window_start}, window_end={window_end}")` temporarily in `scheduler_node`.
2. With `goal_start_date = "2026-03-23"` (next Monday), confirm the log shows `window_start` ≈ `2026-03-23T00:00:00+00:00` (midnight in user's timezone, converted to UTC), not today.

### Test 3 — Pre-fan-out date collection (UX fix)
1. Start fresh. Send: "I want to run a 5K."
2. Confirm `ask_start_date` fires right after clarification questions are answered — **before** any plan is presented.
3. Reply: "this Saturday."
4. Confirm the full plan is presented in one turn with tasks anchored to Saturday.
5. Say "Looks good." On approval, confirm LangSmith trace shows `orchestrator → save_tasks` directly — **no `reschedule` node** in the trace.

### Test 4 — Dedup guard
1. Create a recurring "Morning Run" task with `scheduled_at` = next Monday (the planned start date).
2. Start a new goal with start date = next Monday.
3. Inspect `existing_tasks_data` — "Morning Run" at that Monday slot must appear exactly once (`is_projected: false`), not twice.

### Test 5 — NEXT_MILESTONE unaffected
1. Trigger a milestone completion. Send the NEXT_MILESTONE message.
2. Confirm `ask_start_date` does **not** fire (trace goes `orchestrator → goal_planner` directly).
3. Confirm scheduler runs and produces valid slots (using `now()` as window start).

### Test 6 — Sub-agent output reset on START_DATE
1. Complete a full goal planning flow (all sub-agent outputs set in state).
2. Without clearing the conversation, start a new goal. Reply to the start-date question.
3. Confirm `route_from_goal_planner` triggers the fan-out (all three sub-agents run again).
4. This verifies the `classifier_output/scheduler_output/pattern_output = None` reset in `orchestrator_node`'s START_DATE handler.

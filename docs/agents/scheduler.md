# Scheduler Agent

> Last verified: 2026-03-01

## What it does

Finds free time slots for **drifted** tasks (today and tomorrow). Returns 1–2 suggested slots with a short rationale for each, and applies the user’s choice (reschedule to a new time or skip). Uses user profile (sleep window, work hours) and existing tasks to avoid conflicts. Stateless singleton in-process.

## How to run

Part of the main Flux backend.

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Scheduler is invoked via the `/scheduler` router. One `SchedulerAgent` instance is reused for all requests.

## Connection

- **Today:** HTTP. Orchestrator or frontend calls the endpoints below.
- **Planned (LangGraph):** In-process `scheduler` node for both (1) direct **RESCHEDULE_TASK** flow and (2) fan-out from `goal_planner` (parallel with classifier and pattern_observer). Input: state with `task_id` (and for goal flow: `goal_draft`, `user_profile`). Output: slot suggestions and/or applied result in state.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scheduler/suggest` | Get 1–2 reschedule options for a drifted task. Body: `event_id` (task UUID). Returns suggestions with `new_start`, `new_end`, `label`, `rationale`, plus `skip_option`, `ai_message`. |
| POST | `/scheduler/apply` | Apply reschedule or skip. Body: `event_id`, `action` (`"reschedule"` or `"skip"`). For reschedule, include `new_start`, `new_end`. Returns `new_state`, `message`. |

Defined in [backend/app/routers/scheduler.py](../../backend/app/routers/scheduler.py). Schemas in [backend/app/models/schemas.py](../../backend/app/models/schemas.py).

## Request / response (key fields)

- **SchedulerSuggestRequest:** `event_id` (UUID of the drifted task).
- **SchedulerSuggestResponse:** `event_id`, `task_title`, `suggestions` (each: `new_start`, `new_end`, `label`, `rationale`), `skip_option` (bool), `ai_message` (string).
- **SchedulerApplyRequest:** `event_id`, `action` (`"reschedule"` | `"skip"`), optional `new_start`, `new_end` (required when action is reschedule).
- **SchedulerApplyResponse:** `event_id`, `action`, `new_state` (e.g. `scheduled`, `missed`), optional `new_start`/`new_end`, `message`.

## When the orchestrator uses it

Route here when **intent = RESCHEDULE_TASK**. The orchestrator should have `task_id` (e.g. from `OrchestratorOutput.task_id`).

1. Call `POST /scheduler/suggest` with `event_id` = `task_id`.
2. Present the `suggestions` (and “Skip today” if `skip_option` is true) to the user.
3. On user choice: call `POST /scheduler/apply` with `event_id`, `action`, and if reschedule the chosen `new_start` and `new_end`.

In the LangGraph goal-planning flow, the `scheduler` node is invoked in parallel with classifier and pattern_observer; it receives `goal_draft` and `user_profile` and returns slot/conflict information for the planner to merge into the proposed plan.

## Dependencies

- **DB:** Supabase via `scheduler_service` (fetch task by ID, user profile, tasks in range, update task times, mark missed). See [backend/app/services/scheduler_service.py](../../backend/app/services/scheduler_service.py).
- **Config:** [backend/app/config.py](../../backend/app/config.py): `scheduler_cutoff_hour`, `scheduler_buffer_minutes`, `scheduler_use_llm_rationale` (template vs LLM-generated rationale).

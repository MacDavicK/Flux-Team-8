> ⚠️ **NOT YET IMPLEMENTED** — This agent is planned. The directory `backend/pattern_observer/` exists but is not mounted in the main app.

# Pattern Observer Agent (Planned)

> Last verified: 2026-03-01

## What it does

(From TSD §6.5.) Behavioral analysis: suggests **avoid slots** (e.g. “user often skips Monday morning”) and **category performance** to improve scheduling. Used in the goal_planner fan-out (parallel with classifier and scheduler). Optionally, a **standalone** HTTP service exists in the repo: [backend/pattern_observer](../../backend/pattern_observer) with prefix `/api/pattern-observer`.

## How to run

- **As LangGraph node (planned):** In-process. No separate process.
- **As standalone service (pattern_observer):** Run the pattern_observer app (see its `main.py` or README). Endpoints are under `/api/pattern-observer` (e.g. GET patterns, POST analysis). Can be mounted on another app or run on its own port.

## Connection

- **Planned (LangGraph):** In-process node. Input: state with `user_id`, `user_profile` (and optionally `goal_draft`). Output: e.g. `PatternObserverOutput` (avoid slots, category performance) merged into state for the Goal Planner to use.
- **HTTP (pattern_observer):** If using the standalone module, base path `/api/pattern-observer`. See [backend/pattern_observer/routes.py](../../backend/pattern_observer/routes.py) for exact paths (e.g. GET, POST).

## When the orchestrator uses it

The orchestrator does **not** route to the Pattern Observer directly. The **Goal Planner** node fans out to `pattern_observer` (with `classifier` and `scheduler`). When implementing the graph:

- Pass `user_id` and `user_profile` into the node.
- The node returns pattern suggestions (e.g. “avoid Monday 7–9 AM”, “fitness tasks have high completion on Tuesday/Thursday”) that the Goal Planner merges into the proposed plan.

## Implementation references

- **TSD §6.5:** [flux-tsd.md](../flux-tsd.md) — PatternObserverOutput, avoid slots, category performance, cold-start strategy.
- **Phase 3:** [backend-implementation-plan.md](../backend-implementation-plan.md) — `pattern_observer.py` node, `pattern_observer.txt` prompt.
- **Optional HTTP API:** [backend/pattern_observer/](../../backend/pattern_observer/) — routes and service layer if you want to call Pattern Observer over HTTP instead of as a graph node.

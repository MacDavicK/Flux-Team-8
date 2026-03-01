# Classifier Agent (Planned)

## What it does

(From TSD §6.3.) Classifies a goal or task into **1–3 tags** from a fixed taxonomy. Used in the **goal_planner** fan-out: after the Goal Planner produces a draft plan, the graph runs **classifier**, **scheduler**, and **pattern_observer** in parallel. The classifier’s output (e.g. `ClassifierOutput` with tags) is merged back into state so the Goal Planner can refine the plan or present it to the user.

## How to run

Not implemented as a standalone HTTP service in the current codebase. Planned as a **LangGraph node** only (in-process).

## Connection

- **Planned:** In-process LangGraph node. Input: state containing `goal_draft`, `user_id`. Output: a Pydantic model (e.g. `ClassifierOutput`) merged into state (e.g. `classifier_output`).
- No HTTP API is specified for the classifier in the TSD.

## When the orchestrator uses it

The orchestrator does **not** route to the classifier directly. The **Goal Planner** node, when implemented in the LangGraph graph, fans out to three nodes in parallel via `Send()`:

- `classifier`
- `scheduler`
- `pattern_observer`

All three reconverge to the `goal_planner` node. The orchestrator only routes to `goal_planner` for **GOAL** intent; the graph then invokes the classifier internally.

## Implementation references

- **TSD §6.3:** [flux-tsd.md](../flux-tsd.md) — Classifier output schema, system prompt, model assignment.
- **Phase 3 (agents):** [backend-implementation-plan.md](../backend-implementation-plan.md) — Agent node implementations, prompts (e.g. `classifier.txt`), Pydantic models.
- **Graph wiring:** [flux-tsd.md §7](../flux-tsd.md) — `fan_out_to_subagents` from `goal_planner` to `classifier`, `scheduler`, `pattern_observer`; reconvergence and state reducer.

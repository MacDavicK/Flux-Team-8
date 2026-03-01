# Agents — Orchestrator Connection Guide

This folder documents each Flux agent (and related services) so that anyone working on the **orchestrator** knows how to run and connect to them: endpoints, request/response shapes, and when the orchestrator routes to each.

---

## Agent overview

| Agent | Purpose | How to run | Connection | Doc |
|-------|---------|------------|------------|-----|
| **Goal Planner** | Multi-turn goal decomposition; weekly milestones and tasks | Part of main app | HTTP: `POST /goals/start`, `POST /goals/{id}/respond`, `GET /goals/{id}` | [goal-planner.md](goal-planner.md) |
| **Scheduler** | Reschedule suggestions for drifted tasks; apply or skip | Part of main app | HTTP: `POST /scheduler/suggest`, `POST /scheduler/apply` | [scheduler.md](scheduler.md) |
| **RAG** | Article ingestion and semantic search; used by Goal Planner | Same process as main app | In-process: `rag_service.retrieve()`; HTTP: `POST /api/v1/rag/ingest`, `GET /api/v1/rag/search` | [rag.md](rag.md) |
| **Notifications** | Push, priority, call (escalation) | Mounted on main app when SCRUM routers load | HTTP: `/api/v1/notifications/priority`, `/notifications/push`, `/notifications/call` | [notifications.md](notifications.md) |
| **DAO Service** | Data persistence (users, goals, tasks, etc.) | Separate FastAPI app | HTTP: `/api/v1/users`, `/api/v1/goals`, `/api/v1/tasks`, … | [dao-service.md](dao-service.md) |
| **Classifier** | (Planned) Tags goal/task from taxonomy | LangGraph node | In-process node; fan-out from goal_planner | [classifier.md](classifier.md) |
| **Pattern Observer** | (Planned) Behavioral analysis; avoid slots | LangGraph node or scrum_50 HTTP | In-process or HTTP `/api/pattern-observer` | [pattern-observer.md](pattern-observer.md) |

---

## Orchestrator routing

Today the main backend exposes **HTTP** routers. The TSD describes a **LangGraph** graph where the orchestrator is the entry point and routes by intent. Both views are documented so you can implement the orchestrator either as an HTTP client to existing routes or as LangGraph nodes that call the same logic.

| Intent (or trigger) | Agent | HTTP (today) | LangGraph node (planned) |
|---------------------|-------|--------------|---------------------------|
| **GOAL** | Goal Planner | `POST /goals/start` then `POST /goals/{id}/respond` | `goal_planner` |
| **RESCHEDULE_TASK** | Scheduler | `POST /scheduler/suggest` → user picks → `POST /scheduler/apply` | `scheduler` |
| **NEW_TASK** | Task Handler | (Not yet exposed as dedicated endpoint) | `task_handler` |
| **MODIFY_GOAL** | Goal Modifier | (Not yet exposed) | `goal_modifier` |
| **CLARIFY** | Clarify | N/A | `clarify` → back to orchestrator |
| **ONBOARDING** | Onboarding | N/A | `onboarding` → back to orchestrator |

Goal Planner, when used as a node, fans out in parallel to **classifier**, **scheduler**, and **pattern_observer**; they reconverge to goal_planner. So the Scheduler is both a direct target for `RESCHEDULE_TASK` and a sub-agent in the goal-planning flow.

---

## References

- **Graph structure and intents:** [flux-tsd.md](../flux-tsd.md) (LangGraph, orchestrator output schema, node wiring)
- **Implementation phases:** [backend-implementation-plan.md](../backend-implementation-plan.md) (Phase 3 agents, Phase 4 API)
- **Main app entry:** [backend/app/main.py](../../backend/app/main.py) (routers mounted)

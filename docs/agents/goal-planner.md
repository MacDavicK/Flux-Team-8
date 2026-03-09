# Goal Planner Agent

> Last verified: 2026-03-01

## What it does

Multi-turn goal decomposition for Health & Fitness goals. The agent conducts an empathetic dialogue to extract timeline, current state, target, and preferences, then produces a plan with weekly milestones and recurring tasks. When Pinecone is configured, it uses **RAG** to ground plans in expert content (see [rag.md](rag.md)).

## How to run

Part of the main Flux backend. No separate process.

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Goal Planner is invoked via the `/goals` router. Agent instances are cached in memory per conversation (production would use Redis or similar).

## Connection

- **Today:** HTTP. Orchestrator (or frontend) calls the endpoints below.
- **Planned (LangGraph):** In-process `goal_planner` node; receives state (`user_id`, `conversation_history`, `user_profile`) and returns updated state.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/goals/start` | Start a new goal conversation. Body: `message`, `user_id`. Returns `conversation_id`, `state`, `message`. |
| POST | `/goals/{conversation_id}/respond` | Send the next user message. Body: `message`. Returns updated `state` and assistant `message`. |
| GET | `/goals/{conversation_id}` | Get current conversation state (e.g. for reconnection). |

Defined in [backend/app/routers/goals.py](../../backend/app/routers/goals.py). Schemas in [backend/app/models/schemas.py](../../backend/app/models/schemas.py).

## Request / response (key fields)

- **StartGoalRequest:** `user_id` (UUID), `message` (string).
- **RespondRequest:** `message` (string).
- **GoalConversationResponse:** `conversation_id`, `state` (enum), `message`, optional `suggested_action`, `plan` (list of milestones with `week`, `title`, `tasks`), `goal_id` (set after confirmation).

**ConversationState** values: `IDLE`, `GATHERING_TIMELINE`, `GATHERING_CURRENT_STATE`, `GATHERING_TARGET`, `GATHERING_PREFERENCES`, `PLAN_READY`, `AWAITING_CONFIRMATION`, `CONFIRMED`.

## When the orchestrator uses it

Route to Goal Planner when **intent = GOAL**.

- **HTTP flow:** Orchestrator calls `POST /goals/start` with the user’s first message and `user_id`. For each subsequent user message in that conversation, call `POST /goals/{conversation_id}/respond` with the message. Use `GET /goals/{conversation_id}` to restore state after reconnect.
- **LangGraph:** The `goal_planner` node receives `AgentState` (e.g. `user_id`, `conversation_history`, `user_profile`) and returns updated state (e.g. `goal_draft`, `plan`, next message).

## Dependencies

- **RAG:** In-process `rag_service.retrieve(query)` and `rag_service.format_rag_context(chunks)` in [backend/app/agents/goal_planner.py](../../backend/app/agents/goal_planner.py). Optional; only used when Pinecone is configured.
- **DB:** Supabase via `goal_service` (create/update conversation, persist agent state).
- **Env:** `OPEN_ROUTER_API_KEY` (LLM). For RAG: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (see [rag.md](rag.md)).

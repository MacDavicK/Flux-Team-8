# API Reference

Endpoints exposed by the Flux backend (`app.main:app`). Base URL: `http://localhost:8000` in development.

---

## Goal Planner

| Method | Path | Description |
|--------|------|-------------|
| POST | `/goals/start` | Start a new goal conversation (request body: user message, optional user_id) |
| POST | `/goals/{id}/respond` | Send a message in an ongoing conversation |
| GET | `/goals/{id}` | Get conversation state (for reconnection) |

Conversation flow is stateful; the backend keeps in-memory agent state per conversation. See [backend/app/routers/goals.py](../backend/app/routers/goals.py).

---

## Scheduler

| Method | Path | Description |
|--------|------|-------------|
| GET | `/scheduler/tasks` | List tasks for timeline (today + tomorrow). Query: `user_id` (optional; default demo user) |
| POST | `/scheduler/suggest` | Get reschedule suggestions for a drifted task. Body: `{ "event_id": "<task_id>" }` |
| POST | `/scheduler/apply` | Apply a reschedule (new_start, new_end) or skip. Body: `event_id`, `action` ("reschedule" \| "skip"), optional `new_start`/`new_end` |

Suggest returns 1–2 time slots with rationale; apply updates the task in the database. See [backend/app/routers/scheduler.py](../backend/app/routers/scheduler.py).

---

## RAG (article ingestion and search)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/rag/ingest` | Ingest articles from disk into Pinecone. Query: `articles_dir` (optional), `clear_existing` (default true) |
| GET | `/api/v1/rag/search` | Search the vector store (debug). Query: `q`, optional `top_k` |

Articles live under `backend/articles/` by default. Requires Pinecone and OpenRouter (embedding) config in `backend/.env`. See [backend/app/routers/rag.py](../backend/app/routers/rag.py) and [backend/README.md](../backend/README.md#rag-pipeline).

---

## Notification endpoints (SCRUM 40–44)

Notification escalation (push → WhatsApp → call) is implemented in separate backend modules. They are not mounted on the main FastAPI app; each has its own API prefix and README.

| Module | Prefix / Location | Purpose |
|--------|-------------------|---------|
| SCRUM-40 | `/api/v1/notifications/priority/` | Priority model and escalation path |
| SCRUM-41 | `/notifications/push` | Push notification send |
| SCRUM-42 | `/notifications/whatsapp` | WhatsApp message send |
| SCRUM-43 | (see module README) | Phone call trigger (Twilio Voice) |
| SCRUM-44 | `/api/escalation-demo` | Escalation demo UI API |

For a high-level summary and links to each implementation, see [Notification Escalation](notification-escalation.md).

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{ "status": "ok", "service": "flux-backend" }` |

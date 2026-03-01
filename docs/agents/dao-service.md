# DAO Service (Data Access)

## What it does

Data persistence microservice for Flux: **users**, **goals**, **tasks**, **conversations**, **patterns**, **notification_log**. It exposes CRUD and a few specialized endpoints (e.g. tasks by time range, statistics, bulk update). It contains **no business logic** — that lives in the agents and the main app. Agents (or the main app) use it to read and write canonical data.

## How to run

The DAO service is a **separate** FastAPI app. Run it on its own (different port if the main app is already on 8000):

```bash
cd backend
source venv/bin/activate
# Install dao_service deps if needed (e.g. requirements in dao_service/)
uvicorn dao_service.main:app --reload --port 8001
```

Or run via Docker as documented in [backend/README.md](../../backend/README.md). The main app (`app.main:app`) does **not** mount the DAO routers; they are separate processes unless you explicitly mount them in one app.

## Connection

HTTP. Base URL is wherever the DAO service is running (e.g. `http://localhost:8001`). All endpoints are under prefix **`/api/v1`**.

| Resource | Prefix | Methods | Notes |
|----------|--------|---------|-------|
| **Users** | `/api/v1/users` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` | User profile, onboarded, preferences |
| **Goals** | `/api/v1/goals` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` | Goals with status, plan_json, etc. |
| **Tasks** | `/api/v1/tasks` | GET `/`, GET `/{id}`, GET `/by-timerange`, GET `/statistics`, POST `/`, PATCH `/{id}`, DELETE `/{id}`, POST `/bulk-update-state` | Tasks with status, scheduled_at, trigger_type |
| **Conversations** | `/api/v1/conversations` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}` | LangGraph thread metadata |
| **Patterns** | `/api/v1/patterns` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` | Behavioral pattern signals |
| **Notification log** | `/api/v1/notification-log` | GET `/`, GET `/{id}`, POST `/`, PATCH `/{id}`, DELETE `/{id}` | Delivery audit (push/WhatsApp/call) |
| **Health** | — | GET `/health`, GET `/ready` | Liveness and DB readiness |

Defined in [backend/dao_service/main.py](../../backend/dao_service/main.py) and the `api/v1` routers in `dao_service/api/v1/`.

## When the orchestrator uses it

The orchestrator (and each agent) needs to load **user profile**, **goals**, and **tasks**. Two patterns:

1. **Same process / direct DB:** If the orchestrator runs inside the same repo and uses Supabase directly, it may use existing services (e.g. `goal_service`, `scheduler_service`) that already talk to Supabase. No HTTP call to the DAO service.
2. **Separate DAO service:** If the orchestrator (or a separate service) is designed to talk to a dedicated data API, call the DAO HTTP endpoints above. For example: GET `/api/v1/users/{user_id}` for profile; GET `/api/v1/tasks/by-timerange` for today’s tasks; PATCH `/api/v1/tasks/{id}` to update state after reschedule.

So document in the orchestrator: “User and task data come from either in-process `*_service` (Supabase) or from the DAO service HTTP API.”

## Links

- **User guide (integration examples):** [docs/user_guide_dao.md](../user_guide_dao.md)
- **DAO design (architecture):** [docs/dao_design.md](../dao_design.md)
- **Backend README:** [backend/README.md](../../backend/README.md) (run instructions, entities, test commands)

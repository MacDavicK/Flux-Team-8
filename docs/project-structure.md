# Project Structure

Actual layout of the Flux monorepo (excluding `node_modules`, `.venv`/`venv`, `.git`, and cache dirs).

---

## Repository root

```
Flux/
├── backend/                 # FastAPI backend
│   ├── app/                  # Main application (entry: app.main:app)
│   │   ├── agents/           # AI agents (Goal Planner, Scheduler)
│   │   ├── routers/          # API route handlers (goals, rag, scheduler)
│   │   ├── services/         # Business logic (goal, rag, scheduler services)
│   │   ├── models/           # Pydantic schemas
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── dao_service/          # Legacy DAO microservice (separate from app/)
│   ├── scrum_40_notification_priority_model/
│   ├── scrum_41_push_notification_integration/
│   ├── scrum_42_whatsapp_message_integration/
│   ├── scrum_43_phone_call_trigger/
│   ├── scrum_44_escalation_demo_ui/
│   ├── tests/                # pytest (unit + integration)
│   ├── .env.example
│   ├── Makefile
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/                 # React + TanStack Start + Vite
│   ├── src/
│   │   ├── components/       # UI (flow, chat, modals, navigation, etc.)
│   │   ├── routes/           # TanStack Router file-based routes
│   │   ├── styles/
│   │   ├── utils/            # api.ts (backend client), cn, etc.
│   │   └── ...
│   ├── .env.example
│   └── package.json
├── supabase/
│   ├── migrations/           # SQL migrations (MVP tables, etc.)
│   └── scripts/              # seed_test_data.sql, truncate_tables.sql, etc.
├── scripts/                  # setup.sh, supabase_setup.sh
├── docs/                     # Documentation (this folder)
└── README.md
```

---

## Backend `app/` (primary API)

- **agents:** `goal_planner.py`, `scheduler_agent.py`
- **routers:** `goals.py` (prefix `/goals`), `rag.py` (prefix `/api/v1/rag`), `scheduler.py` (prefix `/scheduler`)
- **services:** `goal_service.py`, `rag_service.py`, `scheduler_service.py`

The run command is: `uvicorn app.main:app --reload` from the `backend/` directory (with venv activated).

---

## Frontend `src/`

- **routes:** File-based (e.g. `index.tsx` = Flow page, `chat.tsx`)
- **components/flow/v2:** FlowTimeline, TimelineEvent, DateHeader, TaskRail
- **components/modals:** RescheduleModal
- **utils/api.ts:** `fetchTimelineTasks`, `fetchSuggestions`, `applyReschedule` (uses `VITE_API_URL`)

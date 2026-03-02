# Flux Backend

FastAPI application for the Flux Life Assistant: Goal Planner, Scheduler, and RAG pipeline.

---

## Project structure

The main application lives under `app/`:

```
backend/
├── app/                   # Main FastAPI application
│   ├── agents/            # AI agents
│   │   ├── goal_planner.py
│   │   └── scheduler_agent.py
│   ├── routers/           # API route handlers
│   │   ├── goals.py
│   │   ├── rag.py
│   │   └── scheduler.py
│   ├── services/          # Business logic & DB access
│   ├── models/            # Pydantic schemas
│   ├── config.py
│   ├── database.py
│   └── main.py
├── conv_agent/            # Voice/conversational agent (REST control plane)
├── dao_service/           # DAO microservice (separate container in docker-compose)
│   ├── main.py
│   ├── api/v1/
│   ├── dao/, models/, schemas/, services/
│   └── scripts/build_and_test.sh
├── tests/                 # pytest (unit + integration)
├── Dockerfile             # Builds main app; dao has its own in dao_service
├── .env.example
├── pytest.ini
└── requirements.txt
```

Legacy `dao_service/` and SCRUM notification modules (scrum_40–44) live alongside `app/` but are not mounted on the main app.

---

## Run locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with SUPABASE_URL, SUPABASE_KEY, OPEN_ROUTER_API_KEY

uvicorn app.main:app --reload
```

API: [http://localhost:8000](http://localhost:8000). Docs: [http://localhost:8000/docs](http://localhost:8000/docs).

Optional: if `make dev` is configured to run `uvicorn app.main:app --reload`, you can use `make dev` instead.

### Running via Docker

From the project root, the main app runs as the `backend` service; the DAO microservice runs as `dao`:

```bash
docker compose up --build   # backend on 8000, dao on 8001, frontend on 3000
docker compose up dao       # DAO only (e.g. for integration tests); health at http://localhost:8001/health
```

---

## Environment variables

Copy from `.env.example`. Key variables (names match `app.config.Settings`; Pydantic reads from `.env`):

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL (e.g. http://127.0.0.1:54321 for local) |
| `SUPABASE_KEY` | Service role key (from `supabase status` when running locally) |
| `OPEN_ROUTER_API_KEY` | OpenRouter API key (Goal Planner + Scheduler + embeddings) |
| `PINECONE_API_KEY` | Optional; required for RAG ingest/search |
| `PINECONE_INDEX_NAME` | Default `flux-articles` |
| `CORS_ORIGINS` | JSON array of allowed origins (e.g. http://localhost:5173) |

Scheduler: `SCHEDULER_CUTOFF_HOUR` (default 21), `SCHEDULER_BUFFER_MINUTES` (default 15), `SCHEDULER_USE_LLM_RATIONALE` (default false). RAG: `RAG_CHUNK_SIZE`, `RAG_TOP_K`, etc. See `app/config.py` for the full list.

---

## API endpoints

Registered in `app/main.py`:

| Router | Endpoints |
|--------|-----------|
| **Goals** | POST `/goals/start`, POST `/goals/{id}/respond`, GET `/goals/{id}` |
| **Scheduler** | GET `/scheduler/tasks`, POST `/scheduler/suggest`, POST `/scheduler/apply` |
| **RAG** | POST `/api/v1/rag/ingest`, GET `/api/v1/rag/search` |
| **System** | GET `/health` |

Full reference: [docs/api-reference.md](../docs/api-reference.md).

---

## Agents

- **Goal Planner** (`app/agents/goal_planner.py`): State-machine agent that uses an LLM (OpenRouter) to decompose goals into weekly milestones and recurring tasks via multi-turn conversation. Can use RAG-retrieved expert context when Pinecone is configured.
- **Scheduler** (`app/agents/scheduler_agent.py`): Finds free time slots for drifted tasks (today/tomorrow), returns 1–2 suggestions with rationale (template or LLM). Uses user profile (sleep/work hours) and existing tasks to avoid conflicts.

---

## Services

- **goal_service**: DB operations for goals, milestones, tasks, conversations (Supabase).
- **scheduler_service**: Fetch tasks in range, get task by ID, user profile, apply reschedule/skip.
- **rag_service**: Load and chunk articles, embed via OpenRouter, upsert to Pinecone; semantic search and format context for the Goal Planner.

---

## Tests

```bash
cd backend
source venv/bin/activate
pytest
```

Config: `pytest.ini` (asyncio_mode=auto, testpaths=tests). Unit and integration tests live under `tests/`.

---

## RAG pipeline

1. **Ingest:** POST `/api/v1/rag/ingest`. Reads articles from `backend/articles/` by default (or pass `articles_dir`). Chunks text, embeds with OpenRouter, upserts to Pinecone. Requires `OPEN_ROUTER_API_KEY` and `PINECONE_API_KEY`.
2. **Search:** GET `/api/v1/rag/search?q=...` for debugging.
3. **Usage:** Goal Planner calls the RAG service to retrieve relevant expert context when building plans (if Pinecone is configured and index is populated).

Create the Pinecone index (e.g. `flux-articles`) in the Pinecone console; dimensions must match the embedding model (e.g. text-embedding-3-small).

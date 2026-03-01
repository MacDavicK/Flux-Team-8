# Getting Started — Flux Backend

Welcome to the Flux backend. This guide walks you through local setup, running the dev server, and executing the test suite.

The backend is a **FastAPI + Python 3.11** application. It serves the core REST API, the conversational (voice) agent control plane, the goal planner, the RAG pipeline, and the scheduler agent — all from a single service started with `uvicorn app.main:app`.

---

## Prerequisites

Before you begin, ensure the following are available on your machine:

| Tool | Minimum Version | Check |
|------|----------------|-------|
| Python | 3.11 | `python3 --version` |
| Docker Desktop | Latest | Required for Supabase |
| Supabase CLI | Latest | `supabase --version` |
| Git | 2.30+ | `git --version` |

Install the Supabase CLI on macOS:

```bash
brew install supabase/tap/supabase
```

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8/backend
```

---

## Step 2: Create a Python Virtual Environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your prompt once the environment is active.

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, uvicorn, SQLAlchemy, Supabase client, LangChain, Pinecone, pytest, and all other dependencies declared in `requirements.txt`.

---

## Step 4: Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values. The minimum set for local development:

```env
# Supabase (local instance — run `supabase status` to get these values)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<anon key from supabase status>
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase status>

# Database (Supabase local PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# AI / LLM via OpenRouter (https://openrouter.ai/keys)
OPEN_ROUTER_API_KEY=<your key>

# Voice / Conversational Agent (https://console.deepgram.com)
DEEPGRAM_API_KEY=<your key>
```

> **Docker users only:** If the backend will run inside a Docker container (via `docker compose`), set `SUPABASE_URL=http://host.docker.internal:54321` so the container can reach the Supabase instance on your host machine.

---

## Step 5: Start Supabase Locally

Docker Desktop must be running before this step.

```bash
# From the project root (Flux-Team-8/)
supabase start
supabase db reset     # applies all migrations and seeds test data
```

Run `supabase status` to confirm the local endpoints are up and to retrieve your API keys.

---

## Step 6: Start the Backend Dev Server

From the `backend/` directory, with your virtual environment active:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

The `--reload` flag watches for file changes and restarts automatically during development.

---

## Step 7: Verify the Server is Running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "service": "flux-backend"}
```

The interactive API documentation (Swagger UI) is available at:

```
http://localhost:8000/docs
```

---

## Running with Docker Compose

To start the full stack (database, backend, and frontend) together:

```bash
# From the project root (Flux-Team-8/)
docker compose up --build
```

The backend container uses `app.main:app` as the entry point and maps to `http://localhost:8000`. See `docs/SETUP.md` for full Docker Compose instructions, including the required `SUPABASE_URL` change for container networking.

---

## Running Tests

The test suite uses pytest. Supabase must be running for integration tests.

### Run all backend tests

```bash
# From the backend/ directory, with venv active
pytest tests/ -v
```

### Run conv_agent tests

```bash
pytest conv_agent/tests/ -v
```

### Run unit tests only (no database required)

```bash
pytest tests/ -v -m "not integration"
```

### Run a specific test file

```bash
pytest tests/test_goals_router.py -v
```

---

## Linting and Formatting

```bash
# Check formatting and lint rules (non-destructive)
make lint

# Auto-fix formatting and lint issues
make format
```

These commands run `black` and `ruff` against the `app/` package.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/goals` | Create a goal |
| `GET` | `/goals` | List goals |
| `POST` | `/api/v1/voice/session` | Start a voice session |
| `POST` | `/api/v1/voice/messages` | Save a transcript message |
| `GET` | `/api/v1/voice/sessions/{id}/messages` | Get session transcript |
| `POST` | `/api/v1/voice/intents` | Process a function-call intent |
| `DELETE` | `/api/v1/voice/session/{id}` | Close a voice session |

The full OpenAPI spec is at `http://localhost:8000/docs` when the server is running.

---

## Voice / Conversational Agent

The conv_agent is part of the main backend service — it requires no separate process. It provides a REST control plane for the Deepgram-powered voice assistant.

To use voice features, set `DEEPGRAM_API_KEY` in `backend/.env`. The voice prompt and function-call intent definitions are loaded from:

- `backend/conv_agent/config/voice_prompt.md`
- `backend/conv_agent/config/intents.yaml`

These paths are relative to `WORKDIR=/app` inside the Docker container, which maps to the `backend/` directory on your host.

---

## Common Issues

### "Module not found" errors on startup

Ensure your virtual environment is active and dependencies are installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Cannot connect to Supabase

1. Confirm Supabase is running: `supabase status`
2. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env` match the values from `supabase status`.
3. If running in Docker, use `SUPABASE_URL=http://host.docker.internal:54321`.

### Port 8000 is already in use

```bash
# macOS / Linux
lsof -i :8000
kill -9 <PID>
```

### Some scrum sprint routers fail to load

You may see a warning on startup like:

```
Warning: Some scrum routers could not be loaded: ...
```

This is expected if optional dependencies (such as VAPID keys for push notifications) are not configured. The core API and conv_agent routes are unaffected.

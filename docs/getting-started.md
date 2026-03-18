# Getting Started

Prerequisites, Quick Start, and manual setup for running Flux locally.

---

## Prerequisites

| Tool | Minimum Version | Download |
|------|-----------------|----------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Python | 3.11+ | [python.org](https://python.org) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com) |
| Docker Desktop | — | [docker.com](https://docker.com) (required for Supabase local) |
| Supabase CLI | — | `brew install supabase/tap/supabase` (macOS) |

---

## Quick Start

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8

# 1. Install frontend & backend dependencies
bash scripts/setup.sh

# 2. Set up Supabase (Docker Desktop must be running)
bash scripts/supabase_setup.sh
```

After setup:

```bash
# Terminal 1 — Frontend
cd frontend && npm run dev

# Terminal 2 — Backend (from repo root)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

Frontend: [http://localhost:3000](http://localhost:3000). Backend API: [http://localhost:8000](http://localhost:8000). API docs: [http://localhost:8000/docs](http://localhost:8000/docs).

> **Note:** The first Supabase run downloads ~2–3 GB of Docker images. Subsequent runs are fast.

---

## Manual Installation

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env` to set `VITE_API_URL` and feature flags (see [Feature Flags](feature-flags.md)).

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with `SUPABASE_URL`, `SUPABASE_KEY`, `OPEN_ROUTER_API_KEY`, and optional `PINECONE_API_KEY` for RAG. See `backend/.env.example` and [backend/README.md](../backend/README.md).

### Supabase (local)

```bash
supabase start
supabase db reset
```

Seed test data (optional):

```bash
docker cp supabase/scripts/seed_test_data.sql supabase_db_Flux-Team-8:/tmp/seed_test_data.sql
docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/seed_test_data.sql
```

---

## Environment Variables

### Backend (`backend/.env`)

Copy from `backend/.env.example`. Key variables:

- **Database:** `SUPABASE_URL`, `SUPABASE_KEY` (from `supabase status` when running locally)
- **AI:** `OPEN_ROUTER_API_KEY` (for Goal Planner and Scheduler; get at [openrouter.ai/keys](https://openrouter.ai/keys))
- **RAG (optional):** `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`
- **CORS:** `CORS_ORIGINS` (default includes localhost:3000)

### Frontend (`frontend/.env`)

Copy from `frontend/.env.example`. Key variables:

- **API:** `VITE_API_URL` (default `http://localhost:8000`)
- **Feature flags:** `VITE_USE_MOCK`, `VITE_ENABLE_DEMO_MODE`, `VITE_ENABLE_VOICE` — see [Feature Flags](feature-flags.md)
- **Supabase (if needed):** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (placeholders only; never commit real keys)

---

## Connecting Frontend to Backend

- **Mock mode (`VITE_USE_MOCK=true`):** The frontend uses in-memory or local mock data. No backend required. Useful when the backend is down or you are working only on UI.
- **Live backend (`VITE_USE_MOCK=false`):** The frontend calls `VITE_API_URL` for timeline tasks, suggestions, and reschedule. Ensure the backend is running (`uvicorn app.main:app --reload`) and CORS allows your dev origin (e.g. `http://localhost:3000`).

Switch by editing `frontend/.env` and restarting `npm run dev`.

---

## Supabase Local URLs

| Service | URL |
|---------|-----|
| Studio (Dashboard) | http://127.0.0.1:54323 |
| API (Project URL) | http://127.0.0.1:54321 |
| Database | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| Email (Mailpit) | http://127.0.0.1:54324 |

```bash
supabase status   # Show URLs and keys
supabase stop     # Stop containers
supabase start    # Start again
supabase db reset # Reset DB and re-apply migrations
```

---

For troubleshooting (ports, venv, Supabase), see [SETUP.md](SETUP.md).

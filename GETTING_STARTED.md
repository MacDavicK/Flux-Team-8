# Getting Started with Flux

This guide walks you through running the full Flux stack locally — backend API, Redis, ngrok tunnel, and the React frontend — in a single command.

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Docker Desktop** | Runs the backend API, Redis, and ngrok | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **Python 3.10+** | Required by the setup script for key generation | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js 20+ & npm** | Runs the frontend dev server | [nodejs.org](https://nodejs.org) |
| **uv** *(optional)* | Faster Python package manager used by the backend | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |

Make sure Docker Desktop is **running** before you start.

---

## External accounts you'll need

You'll be prompted for credentials from the following services during setup. Have them ready:

| Service | Used by | What you need | Where to find it |
|---------|---------|--------------|-----------------|
| **Supabase** | Backend + Frontend | Project URL, anon key, service role key, database URL | [supabase.com/dashboard](https://supabase.com/dashboard) → Settings → API |
| **OpenRouter** | Backend | API key (`sk-or-...`) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Twilio** | Backend | Account SID, Auth Token, phone numbers, Verify service SID | [console.twilio.com](https://console.twilio.com) |
| **LangSmith** *(optional)* | Backend | API key for LangGraph agent tracing | [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys |
| **Sentry** *(optional)* | Backend + Frontend | DSN for error tracking (each has its own project) | Sentry project → Settings → SDK Setup → DSN |
| **ngrok** *(optional)* | Backend | Auth token + static domain for local Twilio webhooks | [dashboard.ngrok.com](https://dashboard.ngrok.com) |

> **Shared values entered once:** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `APP_ENV` are entered once for the backend and automatically copied into `frontend/.env` — no need to type them twice.
>
> **Auto-set frontend defaults:** `VITE_API_URL` defaults to `http://localhost:8000` and `VITE_ENABLE_MOCKS` is set to `false` so the frontend talks directly to your running backend.

---

## One-command setup

From the **repo root**, run:

```bash
bash setup.sh
```

The script will walk you through five steps:

| Step | What it does |
|------|-------------|
| **1 — Dependency check** | Verifies Docker, Python, Node, and npm are available |
| **2 — .env setup** | Creates `backend/.env` and `frontend/.env` from examples. Prompts for each service's credentials. Shared values (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_ENV`) are entered once and automatically mirrored into `frontend/.env`. Already-configured values are skipped automatically. |
| **3 — Migrations** | Applies all SQL files in `backend/migrations/` against your Supabase database (no local `psql` needed — runs inside a Docker container) |
| **4 — Docker (backend)** | Builds and starts the API server, Redis, and ngrok in detached mode; waits for the API to be healthy |
| **5 — Frontend** | Runs `npm install` in `frontend/` then starts the Vite dev server in the foreground |

Press **Enter** to accept any default shown in `[brackets]`. Values already present in your `.env` files are shown with a ✔ and skipped.

---

## Service URLs (once running)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Redis | localhost:6379 |
| ngrok inspector | http://localhost:4040 |

---

## Re-running setup

The script is fully idempotent:

- **Existing `.env` values** are never overwritten — only placeholder values trigger prompts.
- **Migrations** are written to be safe to apply more than once.
- **Docker containers** are stopped and recreated cleanly on each run.

If you only need to restart the services (no env or migration changes), you can run the Docker and frontend steps individually:

```bash
# Backend only
docker compose --project-directory backend --profile ngrok up --build --detach

# Frontend only
npm --prefix frontend run dev
```

---

## Stopping the stack

Press **Ctrl-C** (or **Cmd-C**) to stop the frontend dev server.

`setup.sh` registers a shutdown hook, so stopping the frontend **automatically runs `backend/dev-end.sh --soft`**, which:

- Stops and removes all Docker Compose containers (API, Redis, ngrok)
- Skips volume and build-cache pruning so the next startup is faster

If you need a full teardown (remove volumes and build cache too), run it manually:

```bash
bash backend/dev-end.sh          # full teardown
bash backend/dev-end.sh --soft   # containers only (keep volumes & cache)
```

---

## Project structure

```
.
├── setup.sh            ← this script
├── GETTING_STARTED.md  ← you are here
├── backend/            ← FastAPI + LangGraph API
│   ├── .env            ← created by setup.sh (git-ignored)
│   ├── migrations/     ← SQL migration files
│   └── docker-compose.yml
└── frontend/           ← TanStack Start (React SSR)
    └── .env            ← created by setup.sh (git-ignored)
```

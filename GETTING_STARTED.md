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
| **Pinecone** | Backend (RAG) | API key + index name (default: `flux-articles`) | [app.pinecone.io](https://app.pinecone.io) → API Keys |
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

The script will walk you through six steps:

| Step | What it does |
|------|-------------|
| **1 — Dependency check** | Verifies Docker, Python, Node, and npm are available |
| **2 — .env setup** | Creates `backend/.env` and `frontend/.env` from examples. Prompts for each service's credentials (including Pinecone). Shared values (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `APP_ENV`) are entered once and automatically mirrored into `frontend/.env`. Already-configured values are skipped automatically. |
| **3 — Migrations** | Applies all SQL files in `backend/migrations/` against your Supabase database (no local `psql` needed — runs inside a Docker container) |
| **4 — Docker (backend)** | Builds and starts the API server, Redis, and ngrok (reuses existing tunnel if online); waits for the API to be healthy |
| **5 — RAG ingest** | Checks whether the Pinecone index is already populated. If empty, calls `POST /api/v1/rag/ingest` to embed and upload the 30 health/fitness articles. Skipped automatically on subsequent runs (idempotent). |
| **6 — Frontend** | Runs `npm install` in `frontend/` then starts the Vite dev server in the foreground |

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
- **ngrok** is reused when the endpoint is already online; otherwise a new tunnel is started.

If you only need to restart the services (no env or migration changes), you can run the Docker and frontend steps individually:

```bash
# Backend only
docker compose --project-directory backend --profile ngrok up --build --detach

# Frontend only
npm --prefix frontend run dev
```

---

## Twilio webhooks (local dev)

For WhatsApp replies and voice call DTMF to reach your local app, configure Twilio to use your ngrok URL:

1. **WhatsApp Sandbox:** In [Twilio Console → Messaging → WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/senders/whatsapp-sandbox), set **"When a message comes in"** to:
   ```
   https://<your-ngrok-domain>/api/v1/webhooks/twilio/whatsapp
   ```
   (Replace `<your-ngrok-domain>` with the value of `NGROK_DOMAIN` from `backend/.env`, e.g. `julianne-gonydial-quadrennially.ngrok-free.dev`.)

2. **Voice callbacks:** The backend builds the DTMF callback URL from `TWILIO_WEBHOOK_BASE_URL`. Ensure it matches your ngrok domain (e.g. `https://julianne-gonydial-quadrennially.ngrok-free.dev`).

---

## Troubleshooting: ngrok "endpoint already online" (ERR_NGROK_334)

The setup script **reuses** an existing ngrok tunnel when possible: if the endpoint is already online (e.g. from a previous run where teardown didn't run), it starts only the API and Redis, skipping ngrok. No kill or restart.

If you still see ERR_NGROK_334, the endpoint is held by a zombie session (ngrok cloud hasn't released it). Fix:

1. **Stop from ngrok dashboard:**
   - Go to [dashboard.ngrok.com/endpoints](https://dashboard.ngrok.com/endpoints)
   - Find your domain and stop the active tunnel
   - Wait ~30 seconds, then run `bash setup.sh` again

2. **Temporary workaround** (API and frontend work; Twilio webhooks won't):
   ```bash
   SKIP_NGROK=1 bash setup.sh
   ```

---

## Stopping the stack

Press **Ctrl-C** (or **Cmd-C**) to stop the frontend dev server.

`setup.sh` registers a shutdown hook that automatically stops and removes all Docker Compose containers (API, Redis, ngrok) when you exit.

If you need to tear down the stack manually (e.g. remove volumes and build cache too):

```bash
# Stop containers only
docker compose --project-directory backend --profile ngrok down --remove-orphans

# Full teardown (also remove volumes and build cache)
docker compose --project-directory backend --profile ngrok down --volumes --remove-orphans
docker builder prune --force
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

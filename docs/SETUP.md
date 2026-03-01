# Flux — Development Setup Guide

> **Quick start and run commands:** See [Getting Started](getting-started.md). This file adds troubleshooting and optional details.

---

## System Requirements

| Tool | Minimum Version | Notes |
|------|----------------|-------|
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| Python | 3.11+ | [python.org](https://python.org) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com) |
| Docker Desktop | Latest | Required for Supabase and Docker Compose path |
| Supabase CLI | Latest | `brew install supabase/tap/supabase` (macOS) |

---

## Option A: Docker Compose

Docker Compose builds and starts all three services — PostgreSQL (`5432`), backend (`8000`), and frontend (`5173`) — from a single command. This is the recommended path for integration testing and demo runs.

### 1. Clone and create env files

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### 2. Start Supabase locally

Docker Desktop must be running before this step.

```bash
supabase start
supabase db reset     # applies all migrations and seeds test data
```

Run `supabase status` to print your local API URL and keys.

### 3. Configure backend/.env for Docker networking

When the backend runs inside a Docker container, it cannot reach Supabase at `127.0.0.1`. Update `backend/.env` with the following values (substituting your actual keys from `supabase status`):

```env
# Use host.docker.internal so the backend container can reach the
# Supabase container running on your host machine.
SUPABASE_URL=http://host.docker.internal:54321
SUPABASE_KEY=<anon key from supabase status>
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase status>
```

All other settings (`DATABASE_URL`, `OPEN_ROUTER_API_KEY`, etc.) can remain at their `.env.example` defaults or be filled in as needed.

### 4. Build and start all services

```bash
docker compose up --build
```

The `--build` flag is required on first run and after any Dockerfile change. For subsequent runs without code changes to the Docker images:

```bash
docker compose up
```

### Service URLs

| Service | URL |
|---------|-----|
| Frontend (Vite dev server) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Backend API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### Stop services

```bash
# Stop and remove containers (keeps volume data)
docker compose down

# Stop and remove containers AND all volume data
docker compose down -v
```

---

## Option B: Local Development (without Docker Compose)

Run the backend and frontend directly on your host machine. Supabase still runs in Docker.

### 1. Clone the repository

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8
```

### 2. Start Supabase

Docker Desktop must be running.

```bash
supabase start
supabase db reset     # applies all migrations and seeds test data
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env` if you need to override the API URL or toggle mock mode. The default `VITE_API_URL=http://localhost:8000` is correct for local development.

### 4. Backend setup

**macOS / Linux:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`. The key variables to fill in are:

```env
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=<anon key from supabase status>
SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase status>
OPEN_ROUTER_API_KEY=<your OpenRouter key>
```

### 5. Run the dev servers

Open two terminal windows:

**Terminal 1 — Frontend:**

```bash
cd frontend
npm run dev
# Opens at http://localhost:5173
```

**Terminal 2 — Backend:**

```bash
cd backend
source venv/bin/activate    # or .\venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

---

## Running Tests

### Backend tests

The backend test suite uses pytest. Supabase must be running for integration tests.

```bash
cd backend
source venv/bin/activate

# Run the full test suite (unit + integration)
pytest tests/ -v

# Run unit tests only (no database required)
pytest tests/ -v -m "not integration"

# Run conv_agent tests
pytest conv_agent/tests/ -v
```

### Frontend tests

```bash
cd frontend
npm run type-check    # TypeScript type checking
npm run lint          # ESLint
```

---

## Environment Variables

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | — | Supabase anonymous key |
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_ENABLE_MOCKS` | `false` | Enable MSW mock handlers (bypasses real backend) |

### Backend (`backend/.env`)

| Variable | Example / Default | Description |
|----------|------------------|-------------|
| `DATABASE_URL` | `postgresql://user:password@localhost:5432/flux` | PostgreSQL connection string |
| `SUPABASE_URL` | `http://127.0.0.1:54321` | Supabase local API URL. Use `http://host.docker.internal:54321` when running inside Docker |
| `SUPABASE_KEY` | — | Supabase anon key (from `supabase status`) |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Supabase service role key (bypasses RLS) |
| `OPEN_ROUTER_API_KEY` | — | OpenRouter API key (for GPT-4o-mini and embeddings) |
| `PINECONE_API_KEY` | — | Pinecone API key (for RAG vector store) |
| `SECRET_KEY` | — | JWT signing secret (change before production use) |
| `DEBUG` | `True` | Enable debug logging |
| `DEEPGRAM_API_KEY` | — | Required for voice/conversational agent sessions |

See `backend/.env.example` for the complete list with descriptions.

---

## Common Issues and Troubleshooting

### Backend cannot connect to Supabase when running in Docker

**Symptom:** The backend container starts but logs show connection errors to `127.0.0.1:54321`.

**Cause:** Inside a Docker container, `127.0.0.1` refers to the container itself, not your host machine.

**Fix:** Set `SUPABASE_URL=http://host.docker.internal:54321` in `backend/.env`.

---

### Port 5173 is already in use

```bash
# macOS / Linux
lsof -i :5173
kill -9 <PID>

# Windows
netstat -ano | findstr 5173
taskkill /PID <PID> /F
```

Or change the port in `vite.config.ts` under `server.port`.

---

### Port 8000 is already in use

Same approach as above for port `8000`.

---

### Node version mismatch

```bash
node -v   # Should be 20+
```

Use [nvm](https://github.com/nvm-sh/nvm) (macOS/Linux) to switch versions:

```bash
nvm install 20
nvm use 20
```

---

### Python venv activation fails

| Platform | Command |
|----------|---------|
| macOS / Linux | `source venv/bin/activate` |
| Windows PowerShell | `.\venv\Scripts\Activate.ps1` |
| Windows CMD | `venv\Scripts\activate.bat` |

If PowerShell blocks the script:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### TypeScript errors after pulling

```bash
cd frontend
rm -rf node_modules
npm install
npx tsc --noEmit
```

---

## Recommended VS Code Extensions

This project includes a `.vscode/extensions.json` file. When you open the project in VS Code, you will be prompted to install the recommended extensions. You can also install them manually:

- **Prettier** — Code formatting
- **ESLint** — JavaScript/TypeScript linting
- **Python** + **Pylance** — Python language support
- **GitLens** — Git history and blame annotations
- **Thunder Client** — API testing (lightweight Postman alternative)
- **Auto Rename Tag** — Automatically rename paired HTML/JSX tags

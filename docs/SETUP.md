# Flux — Development Setup Guide

> **Quick start and run commands:** See [Getting Started](getting-started.md). This file adds troubleshooting and optional details.

---

## System Requirements

| Tool | Minimum Version | Download |
|------|----------------|----------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Python | 3.11+ | [python.org](https://python.org) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com) |
| PostgreSQL | 15+ (or Supabase) | [postgresql.org](https://postgresql.org) |
| Docker | Optional | [docker.com](https://docker.com) |

---

## Quick Start (Automated)

The fastest way to get everything installed:

**macOS / Linux:**

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8
bash scripts/setup.sh
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

The setup scripts will check your tool versions, install dependencies, and create `.env` files from the provided examples.

---

## Manual Installation

### 1. Clone the Repository

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env` if you need to change the API URL or toggle mock mode.

### 3. Backend Setup

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

**Windows (Command Prompt):**

```cmd
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` with your database URL, API keys, and secret key.

---

## Running the Dev Servers

### Frontend

```bash
cd frontend
npm run dev
```

Opens at [http://localhost:5173](http://localhost:5173). Hot-reloads on file changes.

### Backend

```bash
cd backend
source venv/bin/activate   # or .\venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --reload
```

Runs at [http://localhost:8000](http://localhost:8000). Auto-reloads on file changes. If you have `make dev` configured to run the same command, you can use that instead.

The API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

---

## Running with Docker

If you prefer containerised development or want to spin up PostgreSQL without installing it locally:

### Start all services

```bash
docker compose up
```

### Start only the database

```bash
docker compose up db
```

This gives you a PostgreSQL 15 instance on port 5432 with credentials:
- User: `flux`
- Password: `flux_dev_password`
- Database: `flux`

### Stop and remove volumes

```bash
docker compose down -v
```

---

## Environment Variables

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_USE_MOCK` | `true` | Use mock API layer (no backend needed) |
| `VITE_API_TIMEOUT` | `10000` | Request timeout in milliseconds |
| `VITE_ENABLE_DEMO_MODE` | `true` | Show demo controls panel |
| `VITE_ENABLE_VOICE` | `false` | Enable voice input (experimental) |
| `VITE_SUPABASE_URL` | — | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | — | Supabase anonymous key |

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | — | OpenAI API key for GPT-4o-mini |
| `SECRET_KEY` | — | JWT signing secret (change in production) |
| `DEBUG` | `true` | Enable debug logging |

See `backend/.env.example` for the full list.

---

## Common Issues & Troubleshooting

### Port 5173 is already in use

Another process (possibly a previous Vite instance) is using the port.

```bash
# Find the process
lsof -i :5173          # macOS / Linux
netstat -ano | findstr 5173   # Windows

# Kill it
kill -9 <PID>          # macOS / Linux
taskkill /PID <PID> /F        # Windows
```

Or change the port in `vite.config.ts` under `server.port`.

### Port 8000 is already in use

Same approach as above, but for port 8000. You can also change the backend port via the `PORT` variable in `backend/.env`.

### Node version mismatch

If you see errors about unsupported syntax or missing APIs:

```bash
node -v   # Should be 18+
```

Use [nvm](https://github.com/nvm-sh/nvm) (macOS/Linux) or [nvm-windows](https://github.com/coreybutler/nvm-windows) to manage Node versions:

```bash
nvm install 18
nvm use 18
```

### Python venv activation fails

The activation command differs by platform:

| Platform | Command |
|----------|---------|
| macOS / Linux | `source venv/bin/activate` |
| Windows PowerShell | `.\venv\Scripts\Activate.ps1` |
| Windows CMD | `venv\Scripts\activate.bat` |

If PowerShell blocks the script, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Supabase connection issues

1. Verify your `SUPABASE_URL` and `SUPABASE_KEY` are correct in `backend/.env`.
2. Check that your IP is allowlisted in the Supabase dashboard under Settings > Database.
3. For local development, set `VITE_USE_MOCK=true` in `frontend/.env` to bypass the backend entirely.

### TypeScript errors after pulling

If you see type errors after pulling new changes:

```bash
cd frontend
rm -rf node_modules
npm install
npx tsc --noEmit
```

---

## Recommended VS Code Extensions

This project includes a `.vscode/extensions.json` file. When you open the project in VS Code, you'll be prompted to install the recommended extensions. You can also install them manually:

- **Prettier** — Code formatting
- **ESLint** — JavaScript/TypeScript linting
- **Python** + **Pylance** — Python language support
- **GitLens** — Git history and blame annotations
- **Thunder Client** — API testing (lightweight Postman alternative)
- **Auto Rename Tag** — Automatically rename paired HTML/JSX tags

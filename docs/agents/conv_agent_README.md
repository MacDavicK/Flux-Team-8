# Flux Conv Agent

> Last verified: 2026-03-02

Voice-first conversational agent for the Flux life assistant. Users speak goals, tasks, and reschedule requests through a real-time Deepgram voice connection. The backend processes three intents (goal creation, task creation, task rescheduling) and persists all data via the Flux DAO Service REST API.

## Architecture

```
Browser                         Backend (FastAPI)            Deepgram
  |                                  |                          |
  |-- POST /voice/session ---------->|                          |
  |<-- { token, config } ------------|                          |
  |                                  |                          |
  |== WebSocket (token auth) ========|=========================>|
  |   Audio PCM  ------------------>                            |
  |                                  |<-- FunctionCallRequest --|
  |-- POST /voice/intents --------->|                           |
  |<-- { result } ------------------|                           |
  |   FunctionCallResponse -------->                            |
  |                                  |                          |
  |<-- TTS Audio (binary) ---------|=========================>  |
  |                                  |                          |
  |-- DELETE /voice/session ------->|                           |
```

**Three intents:**
- `submit_goal_intent` -- Create a multi-week goal
- `submit_new_task_intent` -- Create a time- or location-triggered task
- `submit_reschedule_intent` -- Reschedule an existing task

## Prerequisites

| Requirement       | Version   | Notes                                                      |
|-------------------|-----------|------------------------------------------------------------|
| Python            | 3.11+     | Backend runtime                                            |
| Node.js           | 20+       | Frontend build (matches `frontend/Dockerfile`)             |
| Supabase CLI      | latest    | Required to run Supabase locally (`brew install supabase/tap/supabase`) |
| Docker Desktop    | latest    | Required for `docker compose up` deployment                |
| DEEPGRAM_API_KEY  | --        | Required for live voice (not needed for unit tests)        |

**Important:** The conv_agent does not connect to the database directly. All persistence goes through the DAO Service (`http://localhost:8001`). When running without Docker, start the DAO Service before starting the backend.

## Quick Setup

```bash
# Make the script executable
chmod +x scripts/conv_agent.sh

# Install all dependencies (backend + frontend)
./scripts/conv_agent.sh setup

# Set your Deepgram API key (only needed for live voice)
echo 'DEEPGRAM_API_KEY=your_key_here' >> backend/.env
```

## Running with Mocks (Recommended for Dev)

The mock module (`backend/conv_agent/mocks.py`) provides in-memory replacements for:
- **DAO Service** -- `MockDaoClient` stores conversations, messages, users, tasks, and goals in Python dicts
- **Deepgram token minting** -- Returns `MOCK_DEEPGRAM_TOKEN_FOR_TESTING`

No external services, API keys, or database connections are required to run unit tests.

```bash
# Run conv_agent unit tests
./scripts/conv_agent.sh test

# Or run directly with pytest
cd backend
python -m pytest conv_agent/tests/ -v --tb=short -k "not integration"
```

What gets mocked:
- `conv_agent.dao_client.get_dao_client` -- `MockDaoClient` instance (replaces all DAO Service HTTP calls)
- `conv_agent.voice_service.mint_deepgram_token` -- returns fake token

## Running the Full Stack

### Step 1 — Start Supabase

The project uses [Supabase CLI](https://supabase.com/docs/guides/local-development/cli/getting-started) to run a local Supabase stack (PostgreSQL on port 54322, Studio on port 54323).

**Install the CLI (one-time):**
```bash
# macOS
brew install supabase/tap/supabase

# Linux / WSL
npx supabase
```

**Start Supabase:**
```bash
supabase start
```

`supabase start` boots the local stack but does **not** apply schema automatically — the `supabase/migrations/` directory was consolidated and its contents merged into a single canonical file. Apply the full schema once after starting:

```bash
# Apply the consolidated schema (tables, indexes, RLS, triggers)
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f flux-backend/migrations/001_schema.sql
```

This idempotent script creates all tables including the voice session columns (`voice_session_id`, `extracted_intent`, `intent_payload`, `linked_goal_id`, `linked_task_id`, `ended_at`, `duration_seconds`) on `conversations`, and `input_modality` + `metadata` on `messages`. Safe to run again on an existing database.

To reset the database to a clean state:
```bash
supabase db reset      # drops and recreates the local Postgres instance (DESTROYS local data)
# then re-apply the schema:
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f flux-backend/migrations/001_schema.sql
```

Useful ports after `supabase start`:
| Service         | URL                        |
|-----------------|----------------------------|
| PostgreSQL      | `localhost:54322`          |
| Supabase Studio | `http://localhost:54323`   |
| Supabase API    | `http://localhost:54321`   |

### Step 2 — Start the DAO Service

The DAO service is included in the main `docker-compose.yml`. `docker compose up --build` from the project root starts it alongside the backend and frontend. It is available at `http://localhost:8001` (host) and `http://dao:8001` (container-to-container).

For standalone use:
```bash
# From the project root
docker compose up dao
```

Check it is up:
```bash
curl http://localhost:8001/health
```

### Step 3 — Set environment variables

In `backend/.env`:
```
DEEPGRAM_API_KEY=your_deepgram_key
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
```

### Step 4 — Start the full stack

**Option A — Docker Compose (recommended):**
```bash
# From the project root
docker compose up --build
```

This starts:
- **dao** on `http://localhost:8001` (data persistence microservice)
- **backend** on `http://localhost:8000` (conv_agent + other APIs)
- **frontend** on `http://localhost:3000` (Vite dev server)

**Option B — Local dev (`conv_agent.sh`):**
```bash
./scripts/conv_agent.sh deploy
```

This starts:
- **dao_service** on `http://localhost:8001`
- **backend** on `http://localhost:8080`
- **frontend** on `http://localhost:3000`

Or start services separately:
```bash
# Terminal 1: dao_service
cd backend && uvicorn dao_service.main:app --host 0.0.0.0 --port 8001

# Terminal 2: backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: frontend
cd frontend && npm run dev
```

Open the chat/voice UI and tap the mic button.

### Service URLs reference

| What you want | Docker Compose | Local dev (`conv_agent.sh`) |
|--------------|----------------|------------------------------|
| **App UI (chat + voice)** | http://localhost:3000/chat | http://localhost:3000/chat |
| Backend API docs (Swagger) | http://localhost:8000/docs | http://localhost:8080/docs |
| Backend health check | http://localhost:8000/health | http://localhost:8080/health |
| dao_service health | http://localhost:8001/health | http://localhost:8001/health |
| Supabase API | http://localhost:54321 | http://localhost:54321 |
| Supabase Studio | http://localhost:54323 | http://localhost:54323 |

> **Note:** The backend and dao_service are REST APIs — opening `/` in a browser returns 404. Use `/docs` to browse the API interactively.

## API Reference

All examples use port `8000` (Docker Compose). If running locally via `conv_agent.sh`, replace `8000` with `8080`.

### POST /api/v1/voice/session
Create a new voice session. Returns a Deepgram token and agent configuration.

```bash
curl -X POST http://localhost:8000/api/v1/voice/session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "a1000000-0000-0000-0000-000000000001"}'
```

Response: `{ "session_id": "...", "deepgram_token": "...", "config": { ... } }`

### POST /api/v1/voice/messages
Save a transcript message (fire-and-forget).

```bash
curl -X POST http://localhost:8000/api/v1/voice/messages \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "role": "user", "content": "I want to learn Spanish"}'
```

Response: `{ "message_id": "...", "status": "saved" }`

### GET /api/v1/voice/sessions/{session_id}/messages
Retrieve the full transcript for a session.

```bash
curl http://localhost:8000/api/v1/voice/sessions/{session_id}/messages
```

Response: `{ "session_id": "...", "messages": [ ... ] }`

### POST /api/v1/voice/intents
Process a Deepgram function call (goal, task, or reschedule).

```bash
curl -X POST http://localhost:8000/api/v1/voice/intents \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "...",
    "function_call_id": "fc_123",
    "function_name": "submit_goal_intent",
    "input": {"goal_statement": "Learn guitar", "timeline": "3 months"}
  }'
```

Response: `{ "function_call_id": "fc_123", "result": "Goal created: Learn guitar with a target of 3 months." }`

### DELETE /api/v1/voice/session/{session_id}
Close a voice session.

```bash
curl -X DELETE http://localhost:8000/api/v1/voice/session/{session_id}
```

Response: `{ "session_id": "...", "status": "closed", "message_count": 5 }`

## File Structure

### Backend

```
backend/conv_agent/
  __init__.py              Empty package init
  config.py                Deepgram + DAO Service settings (pydantic-settings)
  schemas.py               Pydantic request/response models
  dao_client.py            HTTP client for DAO Service REST API
  voice_service.py         Token minting, session CRUD, message persistence
  intent_handler.py        Intent routing (goal, task, reschedule)
  router.py                FastAPI router (5 endpoints)
  mocks.py                 In-memory mocks (MockDaoClient) for testing
  config/
    voice_prompt.md        System prompt for the voice agent
    intents.yaml           Intent definitions (3 intents)
  tests/
    __init__.py
    conftest.py            Integration test fixtures (dao_service client, test user)
    test_voice_service.py  Unit tests for voice_service functions
    test_intent_handler.py Unit tests for intent dispatch
    test_router.py         FastAPI endpoint tests
    test_integration.py    Integration tests (needs Supabase + DEEPGRAM_API_KEY)
```

### Frontend

```
frontend/src/conv_agent/
  index.ts                 Barrel export (useVoiceAgent, types)
  types.ts                 TypeScript types (API + Deepgram events)
  api.ts                   REST client for voice endpoints
  DeepgramClient.ts        WebSocket manager (raw, no SDK)
  AudioEngine.ts           Mic capture + TTS playback (Web Audio API)
  useVoiceAgent.ts         React hook orchestrating the full flow
  components/
    VoiceFAB.tsx           Mic button with status-based styling
    VoiceOverlay.tsx       Full-screen voice session overlay
```

## Testing

### Unit tests (no external services needed)

```bash
# All conv_agent unit tests
./scripts/conv_agent.sh test

# Or run directly with pytest
cd backend
python -m pytest conv_agent/tests/ -v --tb=short -k "not integration"

# Specific test file
python -m pytest conv_agent/tests/test_voice_service.py -v
```

### Integration tests (requires Supabase + DEEPGRAM_API_KEY)

Integration tests run against a real local Supabase database and the DAO Service in-process via ASGI transport. They verify the full flow from voice session creation through intent handling to data persistence.

**Prerequisites:**
1. Supabase running locally (`supabase start`)
2. `DEEPGRAM_API_KEY` set in environment or `backend/.env`

**Steps:**
```bash
# 1. Start Supabase
supabase start

# 2. Export your Deepgram key
export DEEPGRAM_API_KEY=your_key_here

# 3. Run integration tests
cd backend
python -m pytest conv_agent/tests/test_integration.py -v --tb=short

# Or use the script (runs unit + integration when DEEPGRAM_API_KEY is set)
./scripts/conv_agent.sh test
```

Integration tests are automatically skipped when `DEEPGRAM_API_KEY` is not set.

### What each test file covers

| File                      | Type        | Coverage                                         |
|---------------------------|-------------|--------------------------------------------------|
| `test_voice_service.py`   | Unit        | Prompt loading, intent loading, session CRUD, build_session_config |
| `test_intent_handler.py`  | Unit        | Goal/task/reschedule intents, unknown intent handling |
| `test_router.py`          | Unit        | All 5 REST endpoints via AsyncClient              |
| `test_integration.py`     | Integration | Full flow: session create, message save, intent handling, session close |

### Adding new tests

1. Add test functions to the appropriate file in `backend/conv_agent/tests/`
2. Use `patch_conv_agent()` context manager for unit tests that need mocked DAO calls
3. Mark integration tests with `@pytest.mark.integration` and `@skip_no_key`
4. Follow the naming convention: `test_<what_it_does>()`

## Common Issues

### Mic permission denied
The browser requires HTTPS or localhost to grant microphone access. Make sure you are accessing the app via `http://localhost:3000` (both Docker and local `conv_agent.sh`), not an IP address.

### Deepgram token error
If you see "Failed to create voice session", check that `DEEPGRAM_API_KEY` is set in `backend/.env`. For local development without a key, run tests with mocks instead.

### DB migration errors
If Supabase tables are missing columns (e.g., `voice_session_id`, `ended_at`, `duration_seconds`), the consolidated schema has not been applied. The `supabase/migrations/` directory is empty so `supabase db reset` alone will not create any tables. Apply the schema manually:

```bash
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f flux-backend/migrations/001_schema.sql
```

To start completely fresh:
```bash
supabase db reset
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f flux-backend/migrations/001_schema.sql
```

### Import errors
If you see `ModuleNotFoundError: No module named 'conv_agent'`, make sure you are running pytest from the `backend/` directory where `conv_agent/` is a top-level package:
```bash
cd backend
python -m pytest conv_agent/tests/ -v
```

## Extending -- Adding a New Intent

1. **Define the intent in YAML** -- Add a new entry to `backend/conv_agent/config/intents.yaml`:
   ```yaml
   - name: submit_my_new_intent
     route: MY_INTENT
     description: >
       Description of when to call this intent.
     parameters:
       - name: param_name
         type: string
         required: true
         description: "What this parameter is"
   ```

2. **Add a handler in intent_handler.py** -- Create a `_handle_my_intent()` function and register it in the `handlers` dict inside `handle_intent()`.

3. **Write a test** -- Add a test in `test_intent_handler.py`:
   ```python
   @pytest.mark.asyncio
   async def test_handle_my_new_intent():
       with patch_conv_agent():
           session_id = await _create_session()
           result = await handle_intent(
               "submit_my_new_intent",
               {"param_name": "value"},
               session_id,
           )
           assert "expected text" in result
   ```

4. **Update the system prompt** -- Edit `backend/conv_agent/config/voice_prompt.md` to tell the voice agent when to call the new intent.

5. **Run tests** to verify:
   ```bash
   ./scripts/conv_agent.sh test
   ```

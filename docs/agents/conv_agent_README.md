# Flux Conv Agent

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

| Requirement       | Version   | Notes                                     |
|-------------------|-----------|-------------------------------------------|
| Python            | 3.11+     | Backend runtime                           |
| Node.js           | 18+       | Frontend build                            |
| DAO Service       | --        | Must be running on port 8001 (see below)  |
| DEEPGRAM_API_KEY  | --        | Required for live voice (not unit tests)  |
| Supabase          | --        | Required for dao_service and integration tests |

**Important:** The conv_agent no longer connects to the database directly. All persistence goes through the DAO Service (`http://localhost:8001`). Start it before running the backend.

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

The mock module (`backend/app/conv_agent/mocks.py`) provides in-memory replacements for:
- **DAO Service** -- `MockDaoClient` stores conversations, messages, users, tasks, and goals in Python dicts
- **Deepgram token minting** -- Returns `MOCK_DEEPGRAM_TOKEN_FOR_TESTING`

No external services, API keys, or database connections are required to run unit tests.

```bash
# Run conv_agent unit tests
./scripts/conv_agent.sh test

# Or run directly with pytest
cd backend
python -m pytest app/conv_agent/tests/ -v --tb=short -k "not integration"
```

What gets mocked:
- `app.conv_agent.dao_client.get_dao_client` -- `MockDaoClient` instance (replaces all DAO Service HTTP calls)
- `app.conv_agent.voice_service.mint_deepgram_token` -- returns fake token

## Running the Full Stack

1. **Start Supabase** (if not already running):
   ```bash
   supabase start
   ```

2. **Set environment variables** in `backend/.env`:
   ```
   DEEPGRAM_API_KEY=your_deepgram_key
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres
   ```

3. **Start all three services** (dao_service + backend + frontend):
   ```bash
   ./scripts/conv_agent.sh deploy
   ```
   This starts:
   - **dao_service** on `http://localhost:8001` (data persistence layer)
   - **backend** on `http://localhost:8080` (conv_agent + other APIs)
   - **frontend** on `http://localhost:3000` (React dev server)

   Or start them separately:
   ```bash
   # Terminal 1: dao_service
   cd backend && uvicorn dao_service.main:app --host 0.0.0.0 --port 8001

   # Terminal 2: backend
   cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

   # Terminal 3: frontend (set VITE_API_BASE so voice API points to backend)
   cd frontend && VITE_API_BASE=http://localhost:8080 npm run dev
   ```

4. Open `http://localhost:3000/chat` and tap the mic button.

### Service URLs reference

| What you want | URL |
|--------------|-----|
| **App UI (chat + voice)** | http://localhost:3000/chat |
| Home / flow view | http://localhost:3000/ |
| Backend API docs (Swagger) | http://localhost:8080/docs |
| Backend health check | http://localhost:8080/health |
| dao_service health | http://localhost:8001/health |
| dao_service readiness | http://localhost:8001/ready |

> **Note:** The frontend (`localhost:3000`) is the React app — this is where the voice UI lives.
> The backend (`localhost:8080`) and dao_service (`localhost:8001`) are REST APIs; opening `/` in a browser returns 404 because they serve no root page. Use `/docs` to browse the backend API interactively.

## API Reference

### POST /api/v1/voice/session
Create a new voice session. Returns a Deepgram token and agent configuration.

```bash
curl -X POST http://localhost:8080/api/v1/voice/session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "a1000000-0000-0000-0000-000000000001"}'
```

Response: `{ "session_id": "...", "deepgram_token": "...", "config": { ... } }`

### POST /api/v1/voice/messages
Save a transcript message (fire-and-forget).

```bash
curl -X POST http://localhost:8080/api/v1/voice/messages \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "role": "user", "content": "I want to learn Spanish"}'
```

Response: `{ "message_id": "...", "status": "saved" }`

### GET /api/v1/voice/sessions/{session_id}/messages
Retrieve the full transcript for a session.

```bash
curl http://localhost:8080/api/v1/voice/sessions/{session_id}/messages
```

Response: `{ "session_id": "...", "messages": [ ... ] }`

### POST /api/v1/voice/intents
Process a Deepgram function call (goal, task, or reschedule).

```bash
curl -X POST http://localhost:8080/api/v1/voice/intents \
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
curl -X DELETE http://localhost:8080/api/v1/voice/session/{session_id}
```

Response: `{ "session_id": "...", "status": "closed", "message_count": 5 }`

## File Structure

### Backend

```
backend/app/conv_agent/
  __init__.py              Empty package init
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
python -m pytest app/conv_agent/tests/ -v --tb=short -k "not integration"

# Specific test file
python -m pytest app/conv_agent/tests/test_voice_service.py -v
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
python -m pytest app/conv_agent/tests/test_integration.py -v --tb=short

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

1. Add test functions to the appropriate file in `backend/app/conv_agent/tests/`
2. Use `patch_conv_agent()` context manager for unit tests that need mocked DAO calls
3. Mark integration tests with `@pytest.mark.integration` and `@skip_no_key`
4. Follow the naming convention: `test_<what_it_does>()`

## Common Issues

### Mic permission denied
The browser requires HTTPS or localhost to grant microphone access. Make sure you are accessing the app via `http://localhost:5173`, not an IP address.

### Deepgram token error
If you see "Failed to create voice session", check that `DEEPGRAM_API_KEY` is set in `backend/.env`. For local development without a key, run tests with mocks instead.

### DB migration errors
If Supabase tables are missing columns (e.g., `voice_session_id`, `ended_at`, `duration_seconds`), run the voice migration:
```bash
# Check supabase/migrations/ for the voice migration SQL
```

### Import errors after restructure
If you see `ModuleNotFoundError: No module named 'app.services.voice_service'`, an import was not updated to the new `app.conv_agent` path. Search for old import paths:
```bash
grep -r "app.services.voice_service\|app.services.intent_handler\|app.routers.voice\|app.models.voice_schemas" backend/
```

## Extending -- Adding a New Intent

1. **Define the intent in YAML** -- Add a new entry to `backend/app/conv_agent/config/intents.yaml`:
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

4. **Update the system prompt** -- Edit `backend/app/conv_agent/config/voice_prompt.md` to tell the voice agent when to call the new intent.

5. **Run tests** to verify:
   ```bash
   ./scripts/conv_agent.sh test
   ```

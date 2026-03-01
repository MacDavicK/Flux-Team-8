# Flux Backend — Usage Guide

This guide covers running the backend server, making API calls, and understanding the core endpoints.

---

## Table of Contents

1. [Starting the Server](#starting-the-server)
2. [API Endpoints](#api-endpoints)
3. [Workflow Examples](#workflow-examples)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

---

## Starting the Server

### Local development

From the `backend/` directory with the virtual environment active:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at `http://localhost:8000`. The `--reload` flag watches for code changes and restarts automatically.

### Docker Compose

From the project root:

```bash
docker compose up --build
```

The backend maps to `http://localhost:8000` on your host. See `docs/SETUP.md` for the full Docker Compose workflow.

---

## API Endpoints

### Base URL

```
http://localhost:8000
```

### Interactive documentation

The Swagger UI is available at `http://localhost:8000/docs`. It lets you explore all endpoints, view request/response schemas, and make test calls directly from the browser.

---

### Health check

**`GET /health`**

Confirms the service is running.

```bash
curl http://localhost:8000/health
```

Response:

```json
{"status": "ok", "service": "flux-backend"}
```

---

### Goals

#### Create a goal

**`POST /goals`**

```bash
curl -X POST http://localhost:8000/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Get fit for my wedding",
    "description": "Lose 15 lbs and improve stamina over 12 weeks",
    "user_id": "your-user-uuid"
  }'
```

Response `201 Created`:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_id": "your-user-uuid",
  "title": "Get fit for my wedding",
  "status": "active",
  "created_at": "2026-03-02T10:00:00Z"
}
```

The AI planner decomposes the goal into weekly milestones and daily tasks asynchronously. Query the goal again after a few seconds to see the `plan_json` field populated.

#### List goals

**`GET /goals?user_id=<uuid>`**

```bash
curl "http://localhost:8000/goals?user_id=your-user-uuid"
```

#### Get a specific goal

**`GET /goals/{goal_id}`**

```bash
curl http://localhost:8000/goals/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

---

### Voice / Conversational Agent

The conv_agent endpoints are at `/api/v1/voice`. They require a running Deepgram API key (`DEEPGRAM_API_KEY` in `backend/.env`).

#### Start a voice session

**`POST /api/v1/voice/session`**

```bash
curl -X POST http://localhost:8000/api/v1/voice/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <supabase-jwt>" \
  -d '{"user_id": "your-user-uuid"}'
```

Response:

```json
{
  "session_id": "sess_...",
  "deepgram_token": "<short-lived-token>",
  "system_prompt": "You are Flux, an empathetic AI life assistant..."
}
```

The frontend uses `deepgram_token` to open a WebSocket directly with Deepgram.

#### Save a transcript message

**`POST /api/v1/voice/messages`**

Called by the frontend when Deepgram emits a `ConversationText` event. Fire-and-forget: errors are logged but the endpoint always returns 200.

```bash
curl -X POST http://localhost:8000/api/v1/voice/messages \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_...",
    "role": "user",
    "content": "I want to lose weight before my wedding"
  }'
```

#### Get session transcript

**`GET /api/v1/voice/sessions/{session_id}/messages`**

```bash
curl http://localhost:8000/api/v1/voice/sessions/sess_.../messages
```

Response:

```json
{
  "session_id": "sess_...",
  "messages": [
    {"role": "user", "content": "I want to lose weight before my wedding", "created_at": "..."},
    {"role": "assistant", "content": "That's a meaningful goal! Tell me about your wedding date...", "created_at": "..."}
  ]
}
```

#### Process a function-call intent

**`POST /api/v1/voice/intents`**

The frontend forwards Deepgram `FunctionCallRequest` events here. The backend routes the call to the appropriate service and returns a text response for Deepgram to speak.

```bash
curl -X POST http://localhost:8000/api/v1/voice/intents \
  -H "Content-Type: application/json" \
  -d '{
    "function_call_id": "fc_123",
    "function_name": "create_goal",
    "input": {"title": "Lose 15 lbs", "description": "Wedding prep"},
    "session_id": "sess_..."
  }'
```

#### Close a session

**`DELETE /api/v1/voice/session/{session_id}`**

```bash
curl -X DELETE http://localhost:8000/api/v1/voice/session/sess_...
```

---

## Workflow Examples

### Example 1: Create a goal and check the plan

```python
import requests
import time

BASE_URL = "http://localhost:8000"
USER_ID = "your-user-uuid"   # must exist in public.users

# 1. Create the goal
response = requests.post(f"{BASE_URL}/goals", json={
    "title": "Learn Machine Learning",
    "description": "Complete a structured 8-week ML curriculum",
    "user_id": USER_ID,
})
goal = response.json()
goal_id = goal["id"]
print(f"Created goal: {goal_id}")

# 2. Wait for the AI planner to run (background task)
time.sleep(5)

# 3. Retrieve the goal to see the generated plan
response = requests.get(f"{BASE_URL}/goals/{goal_id}")
plan = response.json()
print(f"Plan JSON: {plan.get('plan_json')}")
```

### Example 2: Start a voice session

```python
import requests

BASE_URL = "http://localhost:8000"
SUPABASE_JWT = "your-supabase-jwt"   # from Supabase Auth sign-in

response = requests.post(
    f"{BASE_URL}/api/v1/voice/session",
    headers={"Authorization": f"Bearer {SUPABASE_JWT}"},
    json={"user_id": "your-user-uuid"},
)
session = response.json()
print(f"Session ID: {session['session_id']}")
print(f"Deepgram token expires in: use immediately")

# The frontend connects to Deepgram WebSocket using session['deepgram_token']
# and session['system_prompt']
```

---

## Testing

### Run all tests

```bash
# From backend/ with venv active
pytest tests/ -v
```

### Run conv_agent tests

```bash
pytest conv_agent/tests/ -v
```

### Run a specific test file

```bash
pytest tests/test_goals_router.py -v
```

### Run with output on failure

```bash
pytest tests/ -v -s
```

---

## Troubleshooting

### Cannot connect to Supabase

**Symptom:** Startup logs show connection errors, or API calls return `500` with database messages.

**Steps:**
1. Confirm Supabase is running: `supabase status`
2. Check `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env`
3. If running in Docker, use `SUPABASE_URL=http://host.docker.internal:54321`

### Port 8000 is already in use

```bash
# macOS / Linux
lsof -i :8000
kill -9 <PID>
```

### Some sprint routers fail to load

Expected behavior when optional configuration (e.g., VAPID keys for push notifications) is absent. The warning is printed at startup but does not affect the core API or voice endpoints:

```
Warning: Some scrum routers could not be loaded: ...
```

Configure the missing keys in `backend/.env` to enable those features.

### OpenRouter API errors

**Symptom:** Goal planner or RAG endpoints return `500` with an LLM-related error.

**Steps:**
1. Verify `OPEN_ROUTER_API_KEY` is set and valid in `backend/.env`
2. Check your account credits at https://openrouter.ai
3. Confirm `OPENAI_MODEL` is set to a model available under your OpenRouter plan (default: `openai/gpt-4o-mini`)

### Debug logging

Set `DEBUG=True` and `LOG_LEVEL=DEBUG` in `backend/.env` to see detailed request and agent logs in the console.

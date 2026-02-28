# Backend Design

The backend is a **REST-only control plane**. It never touches audio or manages WebSocket connections. Its responsibilities: mint Deepgram tokens, persist messages, process intent function calls.

## File Structure

```
backend/app/
├── config.py                          # Add Deepgram settings here
├── main.py                            # Register voice router
│
├── models/
│   └── voice_schemas.py               # Pydantic models for voice endpoints
│
├── routers/
│   └── voice.py                       # Voice REST endpoints
│
└── services/
    ├── voice_service.py               # Token minting, session CRUD, message persistence
    └── intent_handler.py              # Intent validation + Orchestrator routing
```

No `voice/` subdirectory with WebSocket handlers — all of that complexity is gone. The backend is just services + a router.

**200-line rule:** No file exceeds 200 lines (excluding imports/docstrings).

---

## API Endpoints

### `POST /api/v1/voice/session`

Creates a new voice session. Mints a Deepgram temp token and returns it with the session config so the client can connect directly.

**Request:**
```json
{ "user_id": "string" }
```

**Steps:**
1. Get user_id from request (mock auth for MVP)
2. Load user profile and today's tasks from DB (for context injection)
3. Create conversation record in DB
4. Mint Deepgram temp token via `POST https://api.deepgram.com/v1/auth/grant`
5. Load system prompt from `config/voice_prompt.md`, append user context
6. Load function definitions from `config/intents.yaml`
7. Return token + config to client

**Response:**
```json
{
  "session_id": "uuid",
  "deepgram_token": "eyJ...",
  "config": {
    "system_prompt": "You are Flux, a warm...",
    "functions": [{ "name": "submit_goal_intent", ... }],
    "voice_model": "aura-2-thalia-en",
    "listen_model": "nova-3",
    "llm_model": "gpt-4o-mini",
    "greeting": "Hey! What can I help you with today?"
  }
}
```

The client uses `deepgram_token` to open the Deepgram WebSocket, and `config` to build the Settings message.

---

### `POST /api/v1/voice/messages`

Persists a transcript message. Called by the client for every `ConversationText` event (fire-and-forget).

**Request:**
```json
{
  "session_id": "uuid",
  "role": "user",
  "content": "I want to learn Spanish"
}
```

**Response:**
```json
{ "message_id": "uuid", "status": "saved" }
```

---

### `GET /api/v1/voice/sessions/{session_id}/messages`

Returns all messages for a session, ordered by `created_at`.

**Response:**
```json
{
  "session_id": "uuid",
  "messages": [
    { "id": "uuid", "role": "user", "content": "...", "created_at": "..." },
    { "id": "uuid", "role": "assistant", "content": "...", "created_at": "..." }
  ]
}
```

---

### `POST /api/v1/voice/intents`

Processes a Deepgram `FunctionCallRequest` forwarded by the client. Validates the payload, routes to the Orchestrator, returns a result string the client sends back to Deepgram.

**Request:**
```json
{
  "session_id": "uuid",
  "function_call_id": "fc_123",
  "function_name": "submit_goal_intent",
  "input": {
    "goal_statement": "Learn Spanish",
    "timeline": "3 months"
  }
}
```

**Response:**
```json
{
  "function_call_id": "fc_123",
  "result": "Goal created: Learn Spanish. I'll help you break this down into weekly milestones."
}
```

The client takes `result` and sends it as the `content` field in a `FunctionCallResponse` to Deepgram.

---

### `DELETE /api/v1/voice/session/{session_id}`

Marks the session closed. Updates the conversation record.

**Response:**
```json
{ "session_id": "uuid", "status": "closed", "message_count": 12 }
```

---

## Core Services

### VoiceService

Handles token minting, config loading, session CRUD, and message persistence.

```python
class VoiceService:
    """Token minting, config loading, session CRUD, message persistence."""

    def mint_deepgram_token(self) -> str:
        """POST to Deepgram auth/grant → temp JWT."""

    def load_system_prompt(self) -> str:
        """Read config/voice_prompt.md from disk."""

    def load_intents(self) -> list[dict]:
        """Read config/intents.yaml, convert to Deepgram function definitions."""

    def create_session(self, user_id: str) -> str:
        """Create conversation row in DB. Returns conversation_id."""

    def close_session(self, session_id: str) -> int:
        """Mark conversation closed. Returns message count."""

    def save_message(self, session_id, role, content) -> str:
        """Insert message row. Returns message_id."""

    def get_messages(self, session_id: str) -> list[dict]:
        """Fetch all messages for a session."""
```

### IntentHandler

Routes function calls to the appropriate backend service.

```python
class IntentHandler:
    """Dispatches Deepgram function calls to Orchestrator services."""

    def handle_intent(self, function_name, params, session_id) -> str:
        """
        Dispatch to _handle_goal, _handle_create_task, or _handle_reschedule.
        Returns a result string for FunctionCallResponse.content.
        """

    def _handle_goal(self, params, session_id) -> str:
        """Create goal via existing goal_service.create_goal()."""

    def _handle_create_task(self, params, session_id) -> str:
        """Create task row in DB."""

    def _handle_reschedule_task(self, params, session_id) -> str:
        """Update existing task with new time."""
```

---

## What the Backend Does NOT Do

Compared to the previous backend-relay design, the following are **removed**:

| Removed | Why |
|---------|-----|
| WebSocket endpoint (`WS /voice/session/{id}/ws`) | Client connects directly to Deepgram |
| `DeepgramClient` (Python WebSocket to Deepgram) | No backend-to-Deepgram connection |
| `AudioRelay` (bridges two WebSockets) | No audio relay |
| `EventHandler` (dispatches Deepgram events) | Client handles events directly |
| `SessionRegistry` (in-memory session store) | No long-lived backend state per session |
| `SSEManager` (server-sent events) | No SSE — client gets events from Deepgram directly |
| KeepAlive management | Client sends KeepAlive to Deepgram directly |

The backend is stateless between requests. It just does CRUD + an HTTP call to Deepgram for tokens.

---

## Rate Limiting

| Limit | Value |
|-------|-------|
| Session creation | 5 per user per 10 min |
| Daily sessions | 20 per user |
| Concurrent sessions | 1 per user |

In-memory counter (MVP). Simple dict keyed by user_id with timestamps.

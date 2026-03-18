# Architecture Overview

## What We Are Building

A voice conversation mode for the Flux app. The user taps a mic button, speaks naturally, and the AI extracts their intent through conversation. Once the intent is clear, it is submitted to the existing Goal Planner and Task system.

**Core behaviors:**
- Real-time voice conversation via Deepgram Voice Agent API
- Live transcriptions displayed as chat bubbles
- All messages persisted to the database
- Past conversations loadable and resumable
- Configurable intent registry (YAML) and system prompt (Markdown)
- Ships with three intents: `submit_goal_intent`, `submit_new_task_intent`, `submit_reschedule_intent`

**Auth:** Mocked for now. A `get_current_user()` dependency returns a hardcoded `user_id`.

---

## Deepgram Voice Agent API

The Deepgram Voice Agent API provides a single WebSocket that bundles STT, LLM, and TTS into one managed pipeline. Key capabilities used in this system:

- **Single WebSocket** — browser connects directly, sends mic audio, receives TTS audio and JSON events
- **Pluggable LLM** — GPT-4o-mini by default; swappable to any supported model
- **Pluggable TTS** — Deepgram Aura by default; swappable to any supported voice
- **Built-in function calling** — the LLM invokes client-side functions, which is the mechanism for intent extraction
- **Turn detection** — silence detection and barge-in are handled server-side by Deepgram
- **Temp token auth** — the backend mints a short-lived JWT so the browser connects without exposing the raw API key

---

## High-Level Architecture

The diagram below shows all system components and how they communicate. The browser maintains two independent connections: one REST channel to the `conv_agent` backend and one WebSocket directly to Deepgram. **The backend never handles audio.**

```mermaid
block-beta
  columns 3

  Browser["Browser\n(React PWA)"]
  space
  Deepgram["Deepgram\nVoice Agent API\n(wss://agent.deepgram.com)"]

  space
  space
  space

  ConvAgent["conv_agent\n(FastAPI, port 8000)\nREST control plane"]
  space
  space

  space
  space
  space

  DaoService["dao_service\n(FastAPI, port 8001)\nDatabase CRUD layer"]
  space
  Supabase["Supabase\nPostgreSQL"]

  Browser -- "WebSocket\n(audio + events)" --> Deepgram
  Browser -- "REST\n(session, messages, intents)" --> ConvAgent
  ConvAgent -- "REST\n(token grant)" --> Deepgram
  ConvAgent -- "HTTP REST\n(CRUD)" --> DaoService
  DaoService -- "SQL\n(async SQLAlchemy)" --> Supabase
```

### Key Design Decision: Direct Browser-to-Deepgram Connection

The browser connects **directly** to Deepgram via WebSocket. The `conv_agent` backend is a **REST-only control plane** — it never proxies audio and never manages WebSocket connections.

| Connection | From | To | Carries |
|---|---|---|---|
| Deepgram WebSocket | React PWA | Deepgram | Binary PCM audio + JSON events (transcripts, function calls, status) |
| Session REST | React PWA | conv_agent | Session creation, message persistence, intent processing |
| Token grant | conv_agent | Deepgram | API key authentication to mint short-lived JWT |
| DAO calls | conv_agent | dao_service | All database CRUD operations |

**Benefits of this design:**
- Backend stays simple — pure REST, no WebSocket or audio handling
- Lower latency — audio travels directly to Deepgram, with no intermediate hop
- Less code — no binary frame management, connection bridging, or audio buffering

---

## Token Authentication Flow

Deepgram requires an API key to open its WebSocket. The raw API key is never sent to the browser. Instead:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Browser (React PWA)
    participant Backend as conv_agent (port 8000)
    participant DG as Deepgram Auth API

    Client->>Backend: POST /api/v1/voice/session
    Backend->>DG: POST /v1/auth/grant\n(Authorization: Token <API_KEY>)
    DG-->>Backend: { "access_token": "<jwt>", "expires_in": 3600 }
    Backend-->>Client: { session_id, deepgram_token: "<jwt>", config: {...} }
    Client->>DG: new WebSocket(url, ["token", jwt])\nwss://agent.deepgram.com/v1/agent/converse
    Note over Client,DG: Token only needs to be valid at connection time.\nOnce the WebSocket is open, it stays open.
```

---

## Overall Session Sequence Diagram

This diagram covers the complete session lifecycle: from session creation through an active conversation (including transcript persistence and a function call) through session end.

```mermaid
sequenceDiagram
    autonumber
    participant Client as Browser (React PWA)
    participant Backend as conv_agent (port 8000)
    participant DAO as dao_service (port 8001)
    participant DB as Supabase PostgreSQL
    participant DG as Deepgram Voice Agent

    rect rgb(235, 245, 255)
        Note over Client,DG: Session Start
        Client->>Backend: POST /api/v1/voice/session { user_id }
        Backend->>DAO: POST /conversations (create conversation row)
        DAO->>DB: INSERT INTO conversations
        DB-->>DAO: conversation record
        DAO-->>Backend: { conversation_id }
        Backend->>DG: POST /v1/auth/grant (mint temp JWT)
        DG-->>Backend: { access_token, expires_in }
        Backend-->>Client: { session_id, deepgram_token, config: { system_prompt, functions, voice_model, listen_model, llm_model, greeting } }
        Client->>DG: WebSocket connect\n(subprotocol: ["token", jwt])
        DG-->>Client: Welcome event
        Client->>DG: Settings message (system prompt, functions, audio config)
        DG-->>Client: SettingsApplied event
        DG-->>Client: Binary TTS audio (greeting)
        Client->>Client: Play greeting audio + display transcript
    end

    rect rgb(240, 255, 240)
        Note over Client,DG: During Conversation — Transcript Turn
        Client->>DG: Binary PCM audio (mic stream)
        DG-->>Client: UserStartedSpeaking event
        DG-->>Client: ConversationText { role: "user", content: "..." }
        Client->>Backend: POST /api/v1/voice/messages (fire-and-forget)
        Backend->>DAO: POST /messages (save user message)
        DAO->>DB: INSERT INTO messages
        DG-->>Client: AgentThinking event
        DG-->>Client: ConversationText { role: "assistant", content: "..." }
        Client->>Backend: POST /api/v1/voice/messages (fire-and-forget)
        Backend->>DAO: POST /messages (save assistant message)
        DAO->>DB: INSERT INTO messages
        DG-->>Client: AgentStartedSpeaking event
        DG-->>Client: Binary TTS audio (response)
        DG-->>Client: AgentAudioDone event
    end

    rect rgb(255, 248, 235)
        Note over Client,DG: During Conversation — Function Call (Intent)
        DG-->>Client: FunctionCallRequest { id, function_name, input }
        Client->>Backend: POST /api/v1/voice/intents { session_id, function_call_id, function_name, input }
        Backend->>DAO: Route to intent handler → CRUD operation
        DAO->>DB: INSERT INTO goals / tasks (or UPDATE tasks)
        DB-->>DAO: created/updated record
        DAO-->>Backend: result
        Backend-->>Client: { function_call_id, result: "Confirmation string" }
        Client->>DG: FunctionCallResponse { id, name, content: result }
        DG-->>Client: AgentStartedSpeaking event
        DG-->>Client: Binary TTS audio (confirmation spoken aloud)
        DG-->>Client: AgentAudioDone event
    end

    rect rgb(255, 240, 240)
        Note over Client,DG: Session End
        Client->>DG: WebSocket close
        Client->>Backend: DELETE /api/v1/voice/session/{session_id}
        Backend->>DAO: PATCH /conversations/{id} (set ended_at, duration_seconds)
        DAO->>DB: UPDATE conversations
        DB-->>DAO: updated record
        DAO-->>Backend: { message_count }
        Backend-->>Client: { session_id, status: "closed", message_count }
    end
```

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        User["End User\n(Browser / PWA)"]
    end

    subgraph Edge["Edge / CDN"]
        PWA["React PWA\n(Static — Vercel or similar)"]
    end

    subgraph Proxy["Reverse Proxy / Load Balancer"]
        LB["nginx / Cloud Load Balancer\n(TLS termination)"]
    end

    subgraph AppContainer["Docker Container — port 8000"]
        FastAPI["FastAPI + Uvicorn\n(main app)"]
        ConvRouter["conv_agent router\n(mounted at /api/v1/voice/)"]
        FastAPI --> ConvRouter
    end

    subgraph DAOContainer["Docker Container — port 8001"]
        DAOService["FastAPI + Uvicorn\n(dao_service)"]
    end

    subgraph Cloud["Supabase Cloud"]
        PG["PostgreSQL\n(conversations + messages tables)"]
    end

    subgraph DeepgramCloud["Deepgram Cloud"]
        DGAPI["Deepgram Voice Agent API\nwss://agent.deepgram.com/v1/agent/converse"]
    end

    User -->|"HTTPS"| PWA
    User -->|"HTTPS REST"| LB
    User -->|"WSS (direct)"| DGAPI
    LB -->|"HTTP :8000"| FastAPI
    ConvRouter -->|"HTTP REST :8001"| DAOService
    ConvRouter -->|"HTTPS REST"| DGAPI
    DAOService -->|"TLS PostgreSQL"| PG
```

**Deployment notes:**
- The `conv_agent` router is mounted inside the main FastAPI application — it is not a separate process. Both share port 8000.
- The `dao_service` runs as a separate Docker container on port 8001 and is not publicly accessible — it is called only by the backend.
- Supabase manages connection pooling, backups, and TLS for the database.
- The browser WebSocket to Deepgram is a direct connection — it does not pass through the reverse proxy.

---

## Data Flow Summary

### Session Start
1. Client calls `POST /api/v1/voice/session` — backend creates a conversation row in `dao_service`, mints a Deepgram temp token, loads the system prompt and intent function definitions, then returns all of it to the client.
2. Client opens a WebSocket to `wss://agent.deepgram.com/v1/agent/converse` using the temp token.
3. Client sends a `Settings` message to Deepgram (system prompt, tools, audio config).
4. Deepgram confirms with `SettingsApplied` and speaks the greeting — client plays audio and displays transcript.

### During Conversation
1. Client streams mic audio (binary PCM) directly to Deepgram.
2. Deepgram transcribes speech and sends `ConversationText` events — client displays the text and persists it to the backend via `POST /api/v1/voice/messages` (fire-and-forget).
3. Deepgram generates a response, sends audio and a corresponding transcript — client plays audio, displays text, and persists to backend.
4. If a function call occurs: Deepgram sends `FunctionCallRequest` → client forwards it to `POST /api/v1/voice/intents` → backend routes to the appropriate handler → backend returns a result string → client sends `FunctionCallResponse` to Deepgram → Deepgram speaks the confirmation.

### Session End
1. Client closes the Deepgram WebSocket.
2. Client calls `DELETE /api/v1/voice/session/{id}` — backend marks the conversation closed with `ended_at` and `duration_seconds`.

---

## Related Documents

- [Deepgram Integration Details](./02_deepgram_integration.md)
- [Backend Design](./03_backend_design.md)
- [Frontend Design](./04_frontend_design.md)
- [Configuration](./05_configuration.md)
- [Database Schema](./06_database.md)
- [Implementation Plan](./07_implementation_plan.md)

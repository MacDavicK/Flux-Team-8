# Architecture Overview

## What We're Building

A voice conversation mode for the Flux app. The user taps a mic button, speaks naturally, and the AI extracts their intent through conversation. Once the intent is clear, it is submitted to the existing Goal Planner / Task system.

**Core behaviors:**
- Real-time voice conversation via Deepgram Voice Agent API
- Live transcriptions displayed as chat bubbles
- All messages persisted to database
- Past conversations loadable and resumable
- Configurable intent registry (YAML) and system prompt (markdown)
- Ships with three intents: **GOAL**, **NEW_TASK**, **RESCHEDULE_TASK**

**Auth:** Mocked for now. A `get_current_user()` dependency returns a hardcoded user_id.

---

## Why Deepgram Voice Agent (not OpenAI Realtime)

| Concern | Deepgram Voice Agent | OpenAI Realtime |
|---------|---------------------|-----------------|
| Architecture | Single WebSocket — STT + LLM + TTS managed by Deepgram | WebRTC (client) + companion WebSocket (backend) |
| Complexity | One connection, clear event model | Three simultaneous connections to coordinate |
| LLM choice | Pluggable — OpenAI, Anthropic, Groq, etc. | Locked to `gpt-4o-realtime-preview` |
| TTS choice | Pluggable — Deepgram Aura, ElevenLabs, Cartesia, OpenAI | Locked to OpenAI voices |
| Function calling | Built-in, client-side or server-side | Built-in |
| Cost | ~$4.50/hr flat rate | ~$0.60-0.70 per 2-min session (~$18-21/hr) |
| Direct browser connection | Yes — temp token auth, browser connects directly | Yes — via WebRTC with ephemeral key |

---

## Architecture Diagram

```
User's Browser (React PWA)
    |
    |  1. POST /api/v1/voice/session     →  get temp token + config
    |
    |  2. WebSocket to Deepgram (direct)  →  bidirectional audio + events
    |     wss://agent.deepgram.com/v1/agent/converse
    |
    |  3. REST calls to backend           →  persist messages, process intents
    |
    v
[Deepgram Voice Agent API]
    |── STT (Nova-3)         → transcribes user speech
    |── LLM (GPT-4o-mini)   → generates responses + function calls
    |── TTS (Aura)           → synthesizes voice responses

[FastAPI Backend]  ← REST-only control plane (no audio, no WebSocket)
    |
    |── Mint Deepgram temp tokens
    |── Persist messages to DB
    |── Validate & route intents to Orchestrator
    |
    v
[Orchestrator / Goal Planner]  →  [Supabase DB]
```

### Key Design: Direct Browser-to-Deepgram Connection

The browser connects **directly** to Deepgram via WebSocket. The backend **never touches audio** — it is a REST-only control plane.

| Connection | From → To | Carries |
|------------|-----------|---------|
| Deepgram WebSocket | React PWA → Deepgram | Audio (binary) + JSON events (transcripts, function calls, status) |
| REST calls | React PWA → FastAPI | Session creation, message persistence, intent processing |

This is simpler than relaying audio through the backend:
- No backend WebSocket handling
- No binary audio frame management
- No two-WebSocket coordination
- Lower latency (one hop instead of two)

### How Auth Works

Deepgram requires an API key to open its WebSocket. We don't expose the key to the browser. Instead:

1. Backend calls `POST https://api.deepgram.com/v1/auth/grant` with the real API key
2. Deepgram returns a temporary JWT (configurable TTL, up to 1 hour)
3. Backend sends the temp token to the client
4. Client uses the temp token to authenticate the Deepgram WebSocket
5. Token only needs to be valid at connection time — once the WebSocket is open, it stays open

---

## Data Flow Summary

### Session Start
1. Client calls `POST /api/v1/voice/session` → backend creates conversation, mints Deepgram temp token, loads config (system prompt + functions), returns everything to client
2. Client opens WebSocket to `wss://agent.deepgram.com/v1/agent/converse` using temp token
3. Client sends Settings message to Deepgram (system prompt, tools, audio config)
4. Deepgram speaks greeting → client plays audio, displays transcript

### During Conversation
1. Client streams mic audio (binary) directly to Deepgram
2. Deepgram transcribes → sends `ConversationText` → client displays + persists to backend via REST (fire-and-forget)
3. Deepgram generates response → sends audio + transcript → client plays audio + displays + persists
4. If function call: Deepgram sends `FunctionCallRequest` → client forwards to backend REST → backend validates, routes to Orchestrator → returns result → client sends `FunctionCallResponse` to Deepgram

### Session End
1. Client closes Deepgram WebSocket
2. Client calls `DELETE /api/v1/voice/session/{id}` → backend marks conversation closed

---

## Related Documents

- [Deepgram Integration Details](./02_deepgram_integration.md)
- [Backend Design](./03_backend_design.md)
- [Frontend Design](./04_frontend_design.md)
- [Configuration](./05_configuration.md)
- [Database Schema](./06_database.md)
- [Implementation Plan](./07_implementation_plan.md)

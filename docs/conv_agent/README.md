# Voice Conversational Agent — Design Documents

Voice conversation mode for the Flux app, powered by the **Deepgram Voice Agent API**.

The user taps a mic button, speaks naturally, and the AI extracts their intent (goal, task, or reschedule) through conversation. Once the intent is clear, it is submitted to the existing Orchestrator/Goal Planner system.

---

## Documents

| # | Document | What It Covers |
|---|----------|---------------|
| 1 | [Architecture Overview](./01_architecture.md) | High-level system design, data flow, why Deepgram, direct connection auth |
| 2 | [Deepgram Integration](./02_deepgram_integration.md) | WebSocket protocol, message types, audio format, function calling, turn detection |
| 3 | [Backend Design](./03_backend_design.md) | REST-only control plane: endpoints, services, what the backend does NOT do |
| 4 | [Frontend Design](./04_frontend_design.md) | DeepgramClient, AudioEngine, useVoiceAgent hook, UI components |
| 5 | [Configuration](./05_configuration.md) | System prompt, intent registry (YAML), config settings, dynamic context injection |
| 6 | [Database Schema](./06_database.md) | `messages` table, `conversations` alterations, SQLAlchemy models, Pydantic schemas |
| 7 | [Implementation Plan](./07_implementation_plan.md) | 6-phase build order with tasks, tests, and deliverables per phase |

---

## Quick Architecture Summary

```
Browser  ──WebSocket (direct)──▶  Deepgram Voice Agent
  │         (audio + events)        (STT + LLM + TTS)
  │
  │  REST calls:
  │  POST /voice/session    → temp token + config
  │  POST /voice/messages   → persist transcript
  │  POST /voice/intents    → process function call
  │
  ▼
FastAPI Backend  ──▶  Orchestrator  ──▶  Supabase DB
  (REST-only control plane — no audio)
```

The browser connects **directly to Deepgram** for audio. The backend is a REST-only control plane: it mints tokens, persists messages, and routes intents.

---

## Three Intents

| Intent | Trigger | Example |
|--------|---------|---------|
| **GOAL** | User expresses a multi-week aspiration | "I want to learn Spanish" |
| **NEW_TASK** | User wants a reminder or recurring task | "Remind me to call mom at 7pm" |
| **RESCHEDULE_TASK** | User wants to move an existing task | "Move my gym session to Friday" |

Defined in [`config/intents.yaml`](./05_configuration.md#intent-registry--configintentsyaml). Processed via Deepgram function calling.

---

## Key Design Decisions

1. **Deepgram over OpenAI Realtime** — Single WebSocket vs. three connections. Pluggable LLM/TTS. Simpler for a capstone project.

2. **Direct browser-to-Deepgram connection** — Audio flows directly between browser and Deepgram. Backend never touches audio, never manages WebSockets. Uses Deepgram's temporary token API (`POST /v1/auth/grant`) for secure browser auth.

3. **REST-only backend** — No WebSocket endpoints, no audio relay, no event handler, no session registry. Just 5 simple REST endpoints. The backend is stateless between requests.

4. **Client-side function calling** — Functions defined without `endpoint` field. The browser receives `FunctionCallRequest` events from Deepgram and forwards them to the backend REST API for processing.

5. **No Deepgram SDK** — The Deepgram WebSocket API is simple: JSON messages + binary audio frames. A raw `WebSocket` in the browser is cleaner than a SDK dependency.

6. **Existing infra reuse** — Uses the existing Conversation model, goal_service, task tables, and DAO layer. Only adds a `messages` table and voice-specific columns.

7. **Fire-and-forget persistence** — Transcript messages are sent to the backend asynchronously. If a save fails, the transcript still displays locally. Real-time voice flow is never blocked by HTTP round-trips.

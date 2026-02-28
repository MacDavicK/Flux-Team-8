# Implementation Plan

Phased build order. Each phase is independently testable.

---

## Phase 1: Config + Database (Day 1)

**Goal:** Config files exist, database is ready, Pydantic schemas defined.

### Tasks
1. Create `config/voice_prompt.md` with the system prompt
2. Create `config/intents.yaml` with the three intent definitions
3. Add Deepgram settings to `config.py` (`deepgram_api_key`, `deepgram_voice_model`, `deepgram_listen_model`, `deepgram_llm_model`, `deepgram_token_ttl`)
4. Create `backend/app/models/voice_schemas.py` — Pydantic request/response models
5. Run SQL migrations: create `messages` table, alter `conversations` table
6. Add `Message` SQLAlchemy model and Pydantic schemas

### Tests
- `test_voice_schemas` — all Pydantic models serialize/deserialize correctly
- `test_settings_loads_deepgram_key` — Settings loads `DEEPGRAM_API_KEY` from env
- Verify migration: `messages` table exists, `conversations` has new columns

### Deliverable
Config files ready. Database accepts messages.

---

## Phase 2: Backend Services + Router (Day 2-3)

**Goal:** REST API fully working. Can create sessions (mint tokens), persist messages, process intents.

### Tasks
1. Build `voice_service.py` — `mint_deepgram_token()`, `load_system_prompt()`, `load_intents()`, `create_session()`, `close_session()`, `save_message()`, `get_messages()`
2. Build `intent_handler.py` — `handle_intent()` dispatcher → `_handle_goal()`, `_handle_create_task()`, `_handle_reschedule_task()`
3. Build `routers/voice.py` — 5 REST endpoints: `POST /session`, `POST /messages`, `GET /sessions/{id}/messages`, `POST /intents`, `DELETE /session/{id}`
4. Register voice router in `main.py`
5. Add `pyyaml` to `requirements.txt`

### Tests
- `test_mint_deepgram_token` — mock httpx.post, verify correct URL/headers/response parsing
- `test_create_session` — mock Supabase, verify conversation row created
- `test_save_message` — mock Supabase, verify message row inserted
- `test_handle_goal_intent` — mock goal_service.create_goal, verify correct args
- `test_handle_create_task_intent` — verify task row inserted
- `test_handle_unknown_function` — verify error string returned (not exception)
- `test_voice_router_endpoints` — TestClient tests for all 5 endpoints

### Deliverable
Backend fully functional. Can test all endpoints with curl/Postman.

---

## Phase 3: Frontend Types + API Client (Day 3)

**Goal:** TypeScript types and REST client ready for the voice engine.

### Tasks
1. Create `src/types/voice.ts` — types for backend responses + Deepgram WebSocket events
2. Create `src/api/voiceApi.ts` — REST client: `createSession()`, `saveMessage()`, `processIntent()`, `endSession()`

### Tests
- `npx tsc --noEmit` — verify types compile without errors

### Deliverable
Frontend can talk to the backend. Types are ready for the voice engine.

---

## Phase 4: Frontend Voice Engine (Day 4)

**Goal:** Core voice engine works — direct Deepgram WebSocket, mic capture, audio playback.

### Tasks
1. Build `src/voice/DeepgramClient.ts` — WebSocket manager (connect with token, send Settings, handle events, send audio, KeepAlive, FunctionCallResponse)
2. Build `src/voice/AudioEngine.ts` — mic capture via ScriptProcessorNode + TTS playback via AudioContext queue
3. Build `src/voice/useVoiceAgent.ts` — React hook orchestrating DeepgramClient + AudioEngine + voiceApi

### Tests
- Manual browser test: connect to Deepgram, speak, verify audio plays back
- Unit test `float32ToInt16` / `int16ToFloat32` conversions

### Deliverable
Can have a voice conversation from the browser console using `useVoiceAgent`.

---

## Phase 5: Frontend UI Components (Day 5)

**Goal:** Voice button, overlay, and integration into the chat page.

### Tasks
1. Build `src/components/voice/VoiceFAB.tsx` — mic button with animated states
2. Build `src/components/voice/VoiceOverlay.tsx` — full-screen overlay with transcript feed + end button
3. Modify `src/components/chat/ChatInput.tsx` — add voice button (shows when text input empty)
4. Modify `src/routes/chat.tsx` — wire `useVoiceAgent`, render VoiceOverlay, handle toggle

### Tests
- Manual E2E: tap mic → grant permission → speak → see transcript → agent responds → tap end
- Verify existing text chat still works when voice is not active
- Test all voice button states render correctly

### Deliverable
Full voice UI working in the browser.

---

## Phase 6: Polish + Error Handling (Day 6-7)

**Goal:** Robust error handling, rate limiting, conversation history.

### Tasks
1. Add mic permission error handling (show fallback message)
2. Add WebSocket disconnect handling (show error, end session gracefully)
3. Add rate limiting on session creation (in-memory counter)
4. Add conversation history: `GET /api/v1/voice/sessions/{id}/messages` for loading past conversations
5. Test on mobile browser
6. Add intent metadata persistence on conversation record

### Tests
- `test_rate_limit_exceeded` — returns 429
- `test_concurrent_session_blocked` — second session rejected
- Manual: test on mobile Safari and Chrome

### Deliverable
Robust, complete voice agent feature.

---

## Dependency Graph

```
Phase 1 (Config + DB)
    ↓
Phase 2 (Backend Services + Router)
    ↓
Phase 3 (Frontend Types + API Client)
    ↓
Phase 4 (Frontend Voice Engine)
    ↓
Phase 5 (Frontend UI Components)
    ↓
Phase 6 (Polish)
```

Phases 2 and 3 can be parallelized (frontend types only depend on schema shapes, not running backend).
Phase 4 and Phase 2 can be parallelized by two developers.

---

## Tech Stack Summary

| Component | Technology |
|-----------|-----------|
| Backend framework | FastAPI + Uvicorn |
| Backend → Deepgram | httpx (REST only, for token minting) |
| Frontend → Deepgram | Browser native WebSocket (direct connection) |
| Frontend → Backend | fetch (REST calls) |
| Audio format | linear16 PCM, 16kHz, mono |
| STT | Deepgram Nova-3 |
| LLM | GPT-4o-mini (via Deepgram) |
| TTS | Deepgram Aura |
| Database | Supabase PostgreSQL |
| ORM | SQLAlchemy (async) |
| Frontend | React 18 + TypeScript |
| Audio capture | Web Audio API (ScriptProcessorNode) |
| Audio playback | Web Audio API (AudioContext + BufferSource) |
| State management | React hooks (useState/useRef) |
| Styling | Tailwind CSS |

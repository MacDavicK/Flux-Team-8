# Voice Integration Design — Flux

**Status**: Approved for implementation
**Date**: 2026-03-14
**Scope**: Deepgram STT (speech-to-text) + TTS (text-to-speech) for the chat screen

---

## Understanding Summary

- **What**: Voice input/output as an alternative to typed text in the chat UI
- **Why**: Lower friction for goal-setting; speaking is faster and more natural than typing
- **Who**: All users of the chat screen, as an opt-in mode alongside existing text input
- **Key constraint**: The LangGraph orchestrator and all agent nodes are **untouched** — voice is a pure transport layer. Speech → transcript → `onSend()` → same pipeline as typed text
- **Non-goals**: No always-on listening, no wake-word, no voice-only mode, no changes to backend agent logic, no audio stored server-side

---

## Assumptions

1. Deepgram Nova-3 English model for STT; Deepgram Aura `asteria-en` voice for TTS
2. Short-lived Deepgram token TTL: 30 seconds (one per push-to-talk session)
3. Audio format: `audio/webm;codecs=opus` from browser; 16kHz linear16 for Deepgram STT; MP3 for TTS
4. `spoken_summary` field generated in `chat.py` post-graph, not inside LangGraph nodes
5. TTS fires only when the user's most recent turn was a voice input

---

## Architecture

```
FRONTEND                                    BACKEND
┌─────────────────────────────────┐        ┌─────────────────────────────────┐
│  ChatInput                      │        │                                 │
│  ├── text input (unchanged)     │        │  GET /api/v1/voice/token        │
│  └── MicButton (push-to-talk)   │──────→ │  → { token, expires_in: 30 }   │
│       │                         │        │                                 │
│       ↓                         │        │  GET /api/v1/voice/speak        │
│  useVoice hook                  │        │  ?text=<spoken_summary>         │
│  ├── holds Deepgram WS          │        │  → StreamingResponse audio/mpeg │
│  ├── manages mic MediaStream    │        │                                 │
│  └── emits transcript string    │        │  POST /api/v1/chat/message      │
│       │                         │        │  (unchanged)                    │
│       ↓                         │        │  → ChatMessageResponse          │
│  onSend(transcript)             │        │    + spoken_summary: str | None │
│  (same path as typed text)      │        │                                 │
│       │                         │        └─────────────────────────────────┘
│       ↓                         │
│  ChatPage.handleSendMessage()   │
│  (unchanged)                    │
│       │                         │
│       ↓  (if lastInputWasVoice) │
│  GET /api/v1/voice/speak        │──────→  FastAPI → Deepgram Aura → MP3
│  → play via <audio> element     │
└─────────────────────────────────┘
```

---

## Complete Voice Turn Data Flow

1. User presses mic button (`pointerdown`)
   - `useVoice`: `GET /api/v1/voice/token` → `{ token, expires_in: 30 }`
   - `navigator.mediaDevices.getUserMedia({ audio: true })`
   - WebSocket opens: `wss://api.deepgram.com/v1/listen?model=nova-3&language=en&encoding=linear16&sample_rate=16000`
   - Auth: `Authorization: Token <short-lived-token>`

2. User speaks (holding button)
   - `MediaRecorder` chunks → `ws.send(audioBlob)` every 250ms

3. User releases mic button (`pointerup`)
   - `MediaRecorder.stop()`
   - `ws.send(JSON.stringify({ type: "CloseStream" }))`

4. Deepgram returns final transcript
   - `{ channel: { alternatives: [{ transcript: "run 5k every morning" }] }, is_final: true }`

5. `useVoice` sets `transcript`, closes WebSocket
   - `ChatInput` `useEffect` fires: `onSend("run 5k every morning")`
   - `ChatPage` sets `lastInputWasVoice = true`

6. `ChatPage.handleSendMessage("run 5k every morning")`
   - `ChatService.sendMessage(...)` → `POST /api/v1/chat/message`
   - **Identical to typed text path — orchestrator/LangGraph unchanged**

7. `ChatMessageResponse` received
   - `{ message: "...", spoken_summary: "I've built a 4-week plan...", proposed_plan: {...} }`

8. UI renders structured response (e.g. `PlanView`)

9. `lastInputWasVoice === true` → fetch TTS
   - `GET /api/v1/voice/speak?text=...`
   - FastAPI → Deepgram Aura → `StreamingResponse` (`audio/mpeg`)
   - Browser: `audio.src = objectURL` → `audio.play()`
   - Speaker icon animates on AI bubble while playing

10. Audio ends (or user taps to cancel)
    - `lastInputWasVoice = false`, ready for next turn

---

## New Files

| File | Purpose |
|---|---|
| `frontend/src/hooks/useVoice.ts` | STT state machine (token fetch, WebSocket, MediaRecorder) |
| `frontend/src/components/chat/MicButton.tsx` | Push-to-talk button with recording/processing states |
| `backend/app/api/v1/voice.py` | Two endpoints: `GET /token`, `GET /speak` |

## Modified Files

| File | Change |
|---|---|
| `frontend/src/components/chat/ChatInput.tsx` | Render `MicButton` when input empty; watch `transcript` to call `onSend` |
| `frontend/src/routes/chat.tsx` | Track `lastInputWasVoice`; trigger TTS after AI response; cancel on next send |
| `backend/app/main.py` | Register `voice` router |
| `backend/app/models/` | Add `spoken_summary: str \| None = None` to `ChatMessageResponse` |
| `backend/app/api/v1/chat.py` | Call `build_spoken_summary()` after graph runs; set on response |
| `backend/app/config.py` | Add `DEEPGRAM_API_KEY` setting |
| `backend/.env.example` | Add `DEEPGRAM_API_KEY=<your-deepgram-api-key>` |
| `setup.sh` | Add Deepgram API key setup step |

---

## Backend Endpoints

### `GET /api/v1/voice/token`
- **Auth**: required (existing `get_current_user` dependency)
- **Action**: calls Deepgram `POST /v1/keys` with server `DEEPGRAM_API_KEY`, scoped to `usage:write`, TTL 30s
- **Response**: `{ "token": "dg-temp-...", "expires_in": 30 }`

### `GET /api/v1/voice/speak`
- **Auth**: required
- **Query param**: `text` (URL-encoded, max ~500 chars)
- **Action**: calls Deepgram `POST /v1/speak?model=aura-asteria-en`, streams bytes back
- **Response**: `StreamingResponse`, `Content-Type: audio/mpeg`
- **No audio stored server-side**

---

## `spoken_summary` Generation (in `chat.py`)

```python
def build_spoken_summary(response: ChatMessageResponse) -> str:
    if response.proposed_plan:
        n = len(response.proposed_plan.get("milestones", []))
        return f"I've built a {n}-week plan for you. Take a look and tap Activate when you're ready."
    if response.questions:
        n = len(response.questions)
        return f"I have {n} quick question{'s' if n > 1 else ''} to help me plan your goal better."
    if response.options and response.agent_node == "ask_start_date":
        return "When would you like to start? Pick a date below."
    if response.options:
        return "Here are some options for you. Tap one to continue."
    # Plain text: strip markdown, truncate to ~200 chars
    return strip_markdown(response.message)[:200]
```

---

## Frontend Hook API (`useVoice`)

```typescript
// States: idle → requesting_token → ready → recording → transcribing → done → idle

interface UseVoiceReturn {
  startRecording: () => void      // call on pointerdown
  stopRecording: () => void       // call on pointerup / pointerleave
  transcript: string | null       // final transcribed text
  isRecording: boolean
  isProcessing: boolean           // token fetch + transcription in progress
  error: string | null
  reset: () => void               // call after consuming transcript
}
```

---

## Voice UI States

| State | Visual |
|---|---|
| Idle | Mic icon in input bar (faint pulse to invite use) |
| Recording | Full-width pulsing waveform bar, "Listening..." label, red indicator |
| Processing | Spinner (same as existing `ThinkingIndicator`) |
| Speaking (TTS) | Animated speaker icon on AI bubble, "Tap to stop" affordance |

---

## TTS Response Treatment

| Response type | TTS says | Visual UI |
|---|---|---|
| Plain text | Full message (markdown stripped, ≤200 chars) | Text bubble (unchanged) |
| Goal plan | "I've built an N-week plan for you. Tap Activate when ready." | `PlanView` card |
| Clarifier questions | "I have N quick questions to help me plan your goal." | `GoalClarifierView` bottom sheet |
| Start date ask | "When would you like to start? Pick a date below." | `StartDatePicker` |
| Slot options | "Here are some options for you. Tap one to continue." | Option buttons |

---

## Error Handling

| Error | Caught in | User-facing behaviour |
|---|---|---|
| Microphone permission denied | `useVoice` (`getUserMedia` rejected) | Toast: "Microphone access is needed for voice input." Mic button disabled. |
| Token fetch fails | `useVoice` (`apiFetch` throws) | Toast: "Couldn't start voice. Try again." Reset to idle. |
| Deepgram WS connection fails | `useVoice` (`ws.onerror`) | Toast: "Voice unavailable. Try again." Reset to idle. |
| Empty transcript (silence) | `useVoice` (`is_final` with empty string) | Silent reset to idle. No message sent. |
| TTS fetch fails | `ChatPage` (fetch catch) | **Silent** — text response already visible. No error shown. |
| Recording held > 60s | `useVoice` (timeout guard) | Auto-stop, submit whatever transcript arrived. |

---

## Environment Variables

### `backend/.env.example`
```
DEEPGRAM_API_KEY=<your-deepgram-api-key>
```

### `setup.sh` addition
New section in Step 2 (`run_env_setup`):
- Prompt for `DEEPGRAM_API_KEY` with instructions to get it from the Deepgram console
- Skip if already set (consistent with all other keys)

---

## Decision Log

| # | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| 1 | Push-to-talk for STT trigger | Tap-to-start/stop; VAD auto-stop | Explicit control, no accidental triggers, simplest state machine |
| 2 | STT + TTS (full duplex voice) | STT only | User requested both; enables hands-free experience |
| 3 | Spoken summary for structured responses | Read full message verbatim; TTS only for plain text | Keeps TTS brief; structured UI requires visual interaction |
| 4 | TTS only on voice turns | Always play TTS; never play TTS | Respects input modality; typed turns stay text-only |
| 5 | Browser → Deepgram directly via short-lived token | Full FastAPI WebSocket proxy | Lower latency, less server load; API key stays server-side |
| 6 | FastAPI streams TTS audio via `GET /voice/speak` | Inline TTS in chat response | Separate request keeps chat latency unchanged |
| 7 | `spoken_summary` generated in `chat.py` post-graph | Inside LangGraph nodes | Keeps agent nodes clean; single responsibility |
| 8 | Option A architecture (thin layer, 2 new endpoints) | Combined endpoint; full WS proxy | Minimal blast radius; LangGraph/chat pipeline entirely unchanged |
| 9 | TTS failure is silent | Show error toast | Text response already visible; TTS is enhancement only |
| 10 | `DEEPGRAM_API_KEY` added to `setup.sh` | Manual setup only | Consistent with existing onboarding flow |

# Voice Integration — Implementation Plan

**Status**: Ready for implementation
**Date**: 2026-03-14
**Design doc**: [VOICE_DESIGN.md](./VOICE_DESIGN.md)

---

## Overview

Integrate Deepgram STT (speech-to-text) + TTS (text-to-speech) into the chat screen.

- **STT**: Push-to-talk mic button → Deepgram Nova-3 → transcript → same `onSend()` path as typed text
- **TTS**: After AI response on a voice turn, `GET /api/v1/voice/speak` → Deepgram Aura → MP3 stream → play in browser
- **LangGraph/orchestrator**: completely untouched — voice is a transport layer only

---

## Pre-existing Issue (Must Fix Before Phase 3)

`ChatService.sendMessage` in `frontend/src/services/ChatService.ts` currently calls `/orchestrator/message` (an old mock endpoint), not `/api/v1/chat/message`. The `spoken_summary` field from the real backend will never be received until this is fixed. Fix this before starting TTS wiring (Phase 3).

---

## Phase 1 — Backend Infrastructure

**Do these steps in order. Frontend cannot be tested end-to-end until Phase 1 is complete.**

### Step 1 — `backend/app/config.py`
Add `deepgram_api_key: str` to the `Settings` class (after existing secrets).

```python
# Deepgram (Voice)
deepgram_api_key: str
```

> If you want the app to start without a key during dev, make it `deepgram_api_key: str = ""` — the endpoints will fail at runtime but startup won't crash.

---

### Step 2 — `backend/app/models/api_schemas.py`
Add `spoken_summary` to `ChatMessageResponse` (after the `questions` field):

```python
spoken_summary: Optional[str] = None
```

**This must be done before Step 4 and before Step 8 (frontend type).**

---

### Step 3 — `backend/app/api/v1/voice.py` (NEW FILE)

Two endpoints:

**`GET /voice/token`**
- Auth: `get_current_user` dependency (same as all other endpoints)
- Calls Deepgram `POST https://api.deepgram.com/v1/keys` with:
  ```json
  { "comment": "flux-voice-session", "scopes": ["usage:write"], "time_to_live_in_seconds": 30 }
  ```
  Header: `Authorization: Token {settings.deepgram_api_key}`
- Returns: `{ "token": "<dg-temp-key>", "expires_in": 30 }`
- On failure: `HTTPException(502, "Voice token unavailable")` — do not leak Deepgram errors
- Use `httpx.AsyncClient` (async)
- Rate limit: `"10/minute"` (follow existing `limiter` pattern from other routers)

**`GET /voice/speak`**
- Auth: `get_current_user` dependency
- Query param: `text: str = Query(..., max_length=500)`
- Calls `POST https://api.deepgram.com/v1/speak?model=aura-asteria-en` with `{"text": text}`
- Returns: `StreamingResponse(content=..., media_type="audio/mpeg")`
- For ≤200 char text, buffer the full response then return — no need for true streaming
- On failure: `HTTPException(502, "TTS unavailable")`
- Rate limit: `"20/minute"`

Router definition:
```python
router = APIRouter(prefix="/voice", tags=["voice"])
```

> **Gotcha**: Do NOT use `async for chunk in response.aiter_bytes()` inside `StreamingResponse` unless `httpx.AsyncClient` stays open for the lifetime of the stream. For short audio, collect all bytes first, then wrap in `io.BytesIO`.

---

### Step 4 — `backend/app/api/v1/chat.py`

Two sub-tasks:

**4a. Add helpers at top of file (after imports):**

```python
import re

def strip_markdown(text: str) -> str:
    """Remove common markdown syntax for TTS."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    return text.strip()

def build_spoken_summary(response: "ChatMessageResponse") -> str:
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
    return strip_markdown(response.message)[:200]
```

**4b. In `send_message`, refactor the final return into a variable, then set `spoken_summary`:**

```python
resp = ChatMessageResponse(
    conversation_id=...,
    message=reply,
    agent_node=...,
    proposed_plan=...,
    requires_user_action=...,
    options=...,
    questions=...,
)
resp.spoken_summary = build_spoken_summary(resp)
return resp
```

Also update the **RESCHEDULE_TASK short-circuit return** (line ~109) the same way.

> **Do NOT** set `spoken_summary` on `start_onboarding` — leave it as `None` (the default).

---

### Step 5 — `backend/app/main.py`

Add to imports block:
```python
from app.api.v1.voice import router as voice_router
```

Add to router registration block:
```python
app.include_router(voice_router, prefix=_PREFIX)
```

Place after `tasks_router`, before `analytics_router`.

---

### Step 6 — Verify `httpx` dependency

Check `backend/pyproject.toml` or `backend/requirements.txt`. If `httpx` is missing, add `httpx>=0.27`. It is almost certainly already present in a FastAPI project.

---

### Step 7 — `backend/.env.example` + `setup.sh`

**`.env.example`** — add after existing API key sections:
```
# ──────────────────────────────────────────────
# Deepgram (Voice Input / Output)
# ──────────────────────────────────────────────
DEEPGRAM_API_KEY=<your-deepgram-api-key>
```

**`setup.sh`** — add new function:
```bash
setup_deepgram() {
    header "── Deepgram (Voice) ──────────────────────────────"
    info "Sign up and get your API key at: https://console.deepgram.com"
    echo

    local api_key
    api_key="$(get_env DEEPGRAM_API_KEY)"
    if is_placeholder "$api_key"; then
        info "Get your key at: https://console.deepgram.com → API Keys"
        api_key="$(ask "DEEPGRAM_API_KEY (leave blank to skip)" "" "secret")"
        [[ -n "$api_key" ]] && set_env "DEEPGRAM_API_KEY" "$api_key"
    else
        success "DEEPGRAM_API_KEY already set"
    fi
}
```

Call `setup_deepgram` inside `run_env_setup`, after `setup_openrouter` and before `setup_langsmith`.

---

## Phase 2 — Frontend: Minimal STT-Only Path

**After Phase 1 is complete and backend is running.**

### Step 8 — `frontend/src/types/message.ts`

Add to `ChatMessageResponse` interface:
```typescript
spoken_summary?: string | null;
```

---

### Step 9 — `frontend/src/hooks/useVoice.ts` (NEW FILE)

State machine: `idle → requesting_token → recording → transcribing → done → idle`

Public API:
```typescript
interface UseVoiceReturn {
  startRecording: () => void      // call on pointerdown
  stopRecording: () => void       // call on pointerup / pointerleave
  transcript: string | null
  isRecording: boolean            // status === 'recording'
  isProcessing: boolean           // status === 'requesting_token' || 'transcribing'
  error: string | null
  reset: () => void               // call after consuming transcript
}
```

**`startRecording` logic:**
1. Set status → `requesting_token`
2. `apiFetch('/api/v1/voice/token')` — on fail: set error "Couldn't start voice. Try again.", reset to `idle`
3. `navigator.mediaDevices.getUserMedia({ audio: true })` — on permission denial: set error "Microphone access is needed for voice input.", set `micDenied = true`, reset to `idle`
4. Open WebSocket to Deepgram. **Use token as query param** (browser WS API does not support custom headers):
   ```
   wss://api.deepgram.com/v1/listen?model=nova-3&language=en&token=<token>&encoding=opus&container=webm
   ```
   > **Critical**: Use `encoding=opus&container=webm` to match what `MediaRecorder` actually produces (`audio/webm;codecs=opus`). Log `recorder.mimeType` during dev to confirm.
5. Set status → `recording`
6. Create `MediaRecorder` on the stream, `start(250)` (chunks every 250ms). In `ondataavailable`: `if (ws.readyState === WebSocket.OPEN) ws.send(event.data)`
7. Start 60s timeout guard → calls `stopRecording()` on expiry
8. `ws.onmessage`: parse JSON, on `is_final === true` extract `channel.alternatives[0].transcript`. If non-empty → set `transcript`, status → `done`. If empty → silently reset to `idle`.
9. `ws.onerror`: set error "Voice unavailable. Try again.", reset to `idle`

**`stopRecording` logic:**
1. Clear timeout guard
2. `recorder.stop()`
3. Stop all stream tracks (releases browser mic indicator)
4. Set status → `transcribing`
5. `ws.send(JSON.stringify({ type: "CloseStream" }))` — do NOT close WS yet, final transcript still incoming

**`reset` logic:**
- Close WS if open
- `transcript = null`, `error = null`, status → `idle`

**Cleanup**: add `useEffect` cleanup to call `reset()` on unmount (prevents WS leaks when navigating away from `/chat`).

---

### Step 10 — `frontend/src/components/chat/MicButton.tsx` (NEW FILE)

```typescript
interface MicButtonProps {
  onPointerDown: () => void
  onPointerUp: () => void
  isRecording: boolean
  isProcessing: boolean
  disabled?: boolean
}
```

Visual states:
- **Idle**: `Mic` icon from lucide-react, same `w-8 h-8 rounded-full` style as Send button, faint `animate-pulse`
- **Recording**: red background (`bg-red-500`), `MicOff` icon (or pulsing red circle with Framer Motion)
- **Processing**: `Loader2` spin icon from lucide-react

Use `onPointerDown` / `onPointerUp` / `onPointerLeave` (Pointer Events API covers mouse + touch).

---

### Step 11 — `frontend/src/components/chat/ChatInput.tsx`

1. Import `useVoice` from `~/hooks/useVoice` and `MicButton` from `./MicButton`
2. Instantiate the hook inside `ChatInput`
3. Add `useEffect` to consume transcript:
   ```typescript
   useEffect(() => {
     if (transcript) {
       onSend(transcript)
       reset()
     }
   }, [transcript, onSend, reset])
   ```
4. In the `AnimatePresence` block (line ~81), add mic button when `!hasContent`:
   ```tsx
   {!hasContent && (
     <MicButton
       key="mic"
       onPointerDown={startRecording}
       onPointerUp={stopRecording}
       isRecording={isRecording}
       isProcessing={isProcessing}
       disabled={disabled}
     />
   )}
   ```
5. When `isRecording`, set input `placeholder` to `"Listening..."` and `disabled={true}`
6. Show `error` as a toast (or a `motion.p` below the input bar that auto-dismisses after 3s)

### ✅ STT Smoke Test Checkpoint

At this point the full STT path should work:
1. Backend `GET /api/v1/voice/token` → Deepgram token
2. Browser opens Deepgram WS, streams audio
3. Transcript arrives → `onSend(transcript)` → `ChatPage.handleSendMessage` → `POST /api/v1/chat/message`
4. AI responds in chat UI as normal

---

## Phase 3 — TTS Wiring

**Requires Phase 2 complete. Also requires the `ChatService.sendMessage` endpoint bug to be fixed first (see pre-existing issue at top).**

### Step 12 — Add `onVoiceSend` prop to `ChatInput`

Add to `ChatInputProps`:
```typescript
onVoiceSend?: () => void
```

In the transcript `useEffect`, call `onVoiceSend?.()` before `onSend(transcript)`:
```typescript
useEffect(() => {
  if (transcript) {
    onVoiceSend?.()
    onSend(transcript)
    reset()
  }
}, [transcript, onSend, onVoiceSend, reset])
```

---

### Step 13 — Add voice state to `frontend/src/routes/chat.tsx`

Add near top of `ChatPage`:
```typescript
const lastInputWasVoiceRef = useRef<boolean>(false)
const audioRef = useRef<HTMLAudioElement | null>(null)
```

Pass to `ChatInput`:
```tsx
<ChatInput
  onSend={handleSendMessage}
  onVoiceSend={() => { lastInputWasVoiceRef.current = true }}
  disabled={isThinking || isLoadingHistory}
  placeholder="..."
/>
```

Add `playTTS` function:
```typescript
const playTTS = useCallback(async (text: string) => {
  try {
    const encoded = encodeURIComponent(text)
    const response = await apiFetch(`/api/v1/voice/speak?text=${encoded}`)
    if (!response.ok) return  // silent failure
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audioRef.current = audio
    audio.onended = () => {
      URL.revokeObjectURL(url)
      audioRef.current = null
    }
    audio.play().catch(() => {})  // silent failure if user gesture expired
  } catch {
    // Silent failure — text response already visible
  }
}, [])
```

---

### Step 14 — Trigger TTS after AI response

In `handleSendMessage`, after `setMessages(prev => [...prev, aiMessage])` and `setIsThinking(false)`:

```typescript
if (lastInputWasVoiceRef.current && result.spoken_summary) {
  lastInputWasVoiceRef.current = false
  playTTS(result.spoken_summary)
}
```

---

### Step 15 — Cancel TTS on next send

At the top of `handleSendMessage`, before any `setMessages` call:

```typescript
if (audioRef.current) {
  audioRef.current.pause()
  audioRef.current = null
  lastInputWasVoiceRef.current = false
}
```

---

## Phase 4 — Env Setup

### Step 16

Run `bash setup.sh` — it will now prompt for `DEEPGRAM_API_KEY`. Add your key from [console.deepgram.com](https://console.deepgram.com) → API Keys.

---

## Dependency Graph

```
Step 1 (config.py: DEEPGRAM_API_KEY)
    └── Step 3 (voice.py endpoints)
            └── Step 5 (main.py: register router)

Step 2 (api_schemas.py: spoken_summary field)
    └── Step 4 (chat.py: build_spoken_summary)
    └── Step 8 (message.ts: TS type update)
            └── Step 14 (chat.tsx: read spoken_summary)

Step 6 (verify httpx)
    └── Step 3 (voice.py: imports httpx)

Step 7 (.env.example + setup.sh) — independent

Step 9 (useVoice hook)
    └── Step 10 (MicButton)
            └── Step 11 (ChatInput integration)  ← STT smoke test here
                    └── Step 12 (onVoiceSend prop)
                            └── Step 13 (chat.tsx: refs + playTTS)
                                    └── Step 14 (TTS trigger)
                                            └── Step 15 (cancel on send)
```

## Minimal STT-Only Set (skip TTS for now)

Steps: **1, 3, 5, 6, 7, 9, 10, 11** — that's it. Steps 2, 4, 8, 12–15 can be deferred.

---

## Key Gotchas (do not skip these)

| # | Gotcha | Impact |
|---|---|---|
| A | `MediaRecorder` produces `audio/webm;codecs=opus`, not raw PCM. Use `encoding=opus&container=webm` in Deepgram WS params. | Blank transcripts if wrong |
| B | Browser WS API does not support custom headers. Pass token as `?token=<token>` query param. | WS connection fails if using header |
| C | `audio.play()` may be blocked if user gesture context expired. Catch the rejected Promise silently. | Console error / unhandled rejection |
| D | `apiFetch` is client-side only (uses in-memory token). Never call voice endpoints from a server-side loader. | Runtime error |
| E | `ChatService.sendMessage` calls wrong endpoint (`/orchestrator/message`). Fix before Phase 3. | `spoken_summary` never received |
| F | `useVoice` must call `reset()` on unmount. | WebSocket leak on navigation |
| G | `build_spoken_summary` must be called after `ChatMessageResponse` is fully constructed. | Wrong/missing summary |

# Frontend Design

## Overview

The frontend connects **directly to Deepgram** via WebSocket for audio and events. It uses the backend only for REST calls: session creation (get temp token + config), message persistence, and intent processing.

---

## New Files

| File | Purpose |
|------|---------|
| `src/types/voice.ts` | TypeScript types for backend responses + Deepgram WebSocket events |
| `src/api/voiceApi.ts` | REST client for backend voice endpoints |
| `src/voice/DeepgramClient.ts` | WebSocket manager for direct Deepgram connection |
| `src/voice/AudioEngine.ts` | Mic capture (PCM 16kHz) + TTS playback |
| `src/voice/useVoiceAgent.ts` | React hook orchestrating everything |
| `src/components/voice/VoiceFAB.tsx` | Mic button with animated state indicator |
| `src/components/voice/VoiceOverlay.tsx` | Full-screen voice overlay: orb, transcripts, end button |

### Modified Files

| File | Change |
|------|--------|
| `src/components/chat/ChatInput.tsx` | Add voice button (shows when text input is empty) |
| `src/routes/chat.tsx` | Wire `useVoiceAgent` hook, render VoiceOverlay |

---

## `DeepgramClient` — WebSocket Manager

Manages the direct WebSocket connection to `wss://agent.deepgram.com/v1/agent/converse`.

**Responsibilities:**
- Open/close WebSocket with temp token (subprotocol auth)
- Send Settings message on connect
- Parse incoming JSON events and binary audio frames
- Dispatch events via callback interface
- Send KeepAlive every 5s
- Send FunctionCallResponse after intent processing

```typescript
interface DeepgramCallbacks {
  onOpen: () => void;
  onClose: () => void;
  onError: (error: Event) => void;
  onTranscript: (role: "user" | "assistant", content: string) => void;
  onFunctionCall: (id: string, functionName: string, input: Record<string, unknown>) => void;
  onUserSpeaking: () => void;
  onAgentThinking: () => void;
  onAgentSpeaking: () => void;
  onAgentAudioDone: () => void;
  onAudio: (pcmData: ArrayBuffer) => void;
}

class DeepgramClient {
  constructor(token: string, config: SessionConfig, callbacks: DeepgramCallbacks)

  connect(): void          // Open WS, send Settings, start KeepAlive
  disconnect(): void       // Close WS, stop KeepAlive
  sendAudio(pcm: ArrayBuffer): void
  sendFunctionCallResponse(id: string, name: string, content: string): void
}
```

**WebSocket message handling:**
- Binary frames → `onAudio` callback (TTS audio)
- JSON with `type: "ConversationText"` → `onTranscript` callback
- JSON with `type: "FunctionCallRequest"` → `onFunctionCall` callback
- JSON with `type: "UserStartedSpeaking"` → `onUserSpeaking` callback
- Other event types → corresponding callbacks

---

## `AudioEngine` — Mic Capture + TTS Playback

Handles microphone capture and speaker playback using the Web Audio API.

**Capture:** `getUserMedia` → `ScriptProcessorNode` → Float32 to Int16 PCM @ 16kHz
**Playback:** Queue of PCM ArrayBuffers → Int16 to Float32 → `AudioBufferSourceNode` → speakers

```typescript
class AudioEngine {
  async startCapture(onAudioData: (pcm: ArrayBuffer) => void): Promise<void>
  stopCapture(): void

  enqueuePlayback(pcmData: ArrayBuffer): void
  clearPlayback(): void    // for interruption when user starts speaking

  async destroy(): Promise<void>
}
```

**Why `ScriptProcessorNode` (not `AudioWorklet`):** ScriptProcessorNode is deprecated but has 100% browser support including mobile. AudioWorklet requires a separate worker file and has inconsistent mobile support. For a capstone project, reliability wins.

### PCM Conversion

```typescript
// Float32 [-1, 1] → Int16 [-32768, 32767] (for sending to Deepgram)
function float32ToInt16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16;
}

// Int16 → Float32 (for playing Deepgram TTS audio)
function int16ToFloat32(int16: Int16Array): Float32Array {
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }
  return float32;
}
```

---

## `useVoiceAgent` Hook

The primary React interface. Orchestrates `DeepgramClient`, `AudioEngine`, and the backend REST API.

### Interface

```typescript
function useVoiceAgent(userId: string): {
  status: VoiceStatus;       // 'idle' | 'connecting' | 'connected' | 'listening' | 'speaking' | 'error'
  messages: VoiceMessage[];  // transcript messages
  isAgentSpeaking: boolean;
  startSession: () => Promise<void>;
  endSession: () => Promise<void>;
}
```

### Flow

```typescript
async function startSession() {
  // 1. Create session on backend → get temp token + config
  const { session_id, deepgram_token, config } = await voiceApi.createSession(userId);

  // 2. Init AudioEngine (request mic permission)
  const audio = new AudioEngine();

  // 3. Connect to Deepgram directly with temp token
  const client = new DeepgramClient(deepgram_token, config, {
    onTranscript: (role, content) => {
      addMessage(role, content);
      voiceApi.saveMessage(session_id, role, content);  // fire-and-forget
    },
    onFunctionCall: async (id, functionName, input) => {
      const result = await voiceApi.processIntent(session_id, id, functionName, input);
      client.sendFunctionCallResponse(id, functionName, result.result);
    },
    onUserSpeaking: () => {
      audio.clearPlayback();  // interrupt agent playback
    },
    onAudio: (pcm) => {
      audio.enqueuePlayback(pcm);
    },
    // ... other callbacks update status state
  });

  client.connect();

  // 4. Start mic capture → send PCM to Deepgram
  await audio.startCapture((pcm) => client.sendAudio(pcm));
}
```

---

## UI Components

### VoiceFAB

Mic button with animated states. Shown in `ChatInput` when the text input is empty.

| State | Visual |
|-------|--------|
| `idle` | Gray mic icon |
| `connecting` | Pulsing sage |
| `connected` / `listening` | Steady sage glow |
| `speaking` | Animated terracotta (agent is talking) |
| `error` | Red with retry |

### VoiceOverlay

Full-screen overlay shown during an active voice session.

```
+----------------------------------+
|            Voice Chat            |
+----------------------------------+
|                                  |
|  [Scrollable transcript area]    |
|                                  |
|  User: "I want to get fit..."   |
|  AI: "Great! Target date?"      |
|  User: "By June 15th"           |
|  AI: "Done! Goal is set up."    |
|                                  |
+----------------------------------+
|       [Status: Listening...]     |
|          [Pulsing Orb]           |
|       [End Call Button]          |
+----------------------------------+
```

Displays:
- Status indicator (Listening... / Processing... / Speaking...)
- Live transcript feed using existing `ChatBubble` component
- Large end-call button at bottom

---

## Mic Permission Handling

1. On first voice button tap: `navigator.mediaDevices.getUserMedia()` triggers browser permission dialog
2. If denied: show inline message "Mic access is needed for voice mode. You can type instead."
3. If granted: proceed with session

---

## Error Handling

| Error | Handling |
|-------|----------|
| Mic permission denied | Show message, offer text fallback |
| Deepgram WebSocket disconnects | Show "Connection lost. Conversation saved." End session. |
| Backend REST call fails | Log error, continue — transcripts still display locally even if persistence fails |
| Audio playback fails | Silently continue — transcripts still work |
| Intent processing fails | Backend returns error string → Deepgram agent says "trouble setting up" |

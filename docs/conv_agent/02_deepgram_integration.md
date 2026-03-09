# Deepgram Voice Agent Integration

This document covers the Deepgram Voice Agent WebSocket protocol. The **browser connects directly** to Deepgram — the backend never touches audio.

---

## Connection

**Endpoint:** `wss://agent.deepgram.com/v1/agent/converse`

**Auth:** The browser authenticates using a temporary JWT obtained from the backend:
```
// WebSocket subprotocol auth
new WebSocket(url, ["token", tempJWT])
```

**Temp token flow:**
1. Backend calls `POST https://api.deepgram.com/v1/auth/grant` with `Authorization: Token <DEEPGRAM_API_KEY>`
2. Deepgram returns `{ "access_token": "<jwt>", "expires_in": 3600 }`
3. Backend sends the JWT to the client in the session creation response
4. Token only needs to be valid at WebSocket connection time — once open, the connection stays open

No Deepgram SDK needed — the API is a standard WebSocket with JSON + binary messages.

---

## Session Lifecycle

```
1. Client opens WebSocket to Deepgram with temp token
2. Client sends Settings message (JSON) — configures STT, LLM, TTS, tools
3. Deepgram responds: Welcome → SettingsApplied
4. Deepgram speaks greeting (Audio binary frames)
5. Conversation loop: audio in/out + events
6. Client closes WebSocket to end session
```

---

## Messages: Client → Deepgram

### Settings (sent once at session start)

```json
{
  "type": "Settings",
  "audio": {
    "input": { "encoding": "linear16", "sample_rate": 16000 },
    "output": { "encoding": "linear16", "sample_rate": 16000, "container": "none" }
  },
  "agent": {
    "language": "en",
    "listen": {
      "provider": { "type": "deepgram", "model": "nova-3" }
    },
    "think": {
      "provider": { "type": "open_ai", "model": "gpt-4o-mini" },
      "prompt": "<system prompt + user context from backend>",
      "functions": [ "<function definitions from backend>" ]
    },
    "speak": {
      "provider": { "type": "deepgram", "model": "aura-2-thalia-en" }
    },
    "greeting": "Hey! What can I help you with today?"
  }
}
```

The client builds this from the `config` object returned by `POST /api/v1/voice/session`.

### Audio (binary frames)
Raw PCM audio from user's microphone, sent directly to Deepgram.

### FunctionCallResponse
Sent after the client processes a function call (via backend REST):
```json
{
  "type": "FunctionCallResponse",
  "id": "<function_call_id>",
  "name": "submit_goal_intent",
  "content": "{\"status\": \"accepted\", \"goal_id\": \"uuid\"}"
}
```

### KeepAlive
```json
{ "type": "KeepAlive" }
```
Send every 5 seconds during silence to prevent WebSocket timeout.

---

## Messages: Deepgram → Client

### Welcome
```json
{ "type": "Welcome", "request_id": "uuid" }
```
Connection confirmed.

### SettingsApplied
```json
{ "type": "SettingsApplied" }
```
Configuration accepted. Session is ready.

### UserStartedSpeaking
```json
{ "type": "UserStartedSpeaking" }
```
User began talking. Update UI state ("Listening..."). Interrupt agent playback if speaking.

### ConversationText
```json
{
  "type": "ConversationText",
  "role": "user",
  "content": "I want to learn Spanish"
}
```
or
```json
{
  "type": "ConversationText",
  "role": "assistant",
  "content": "Great! Do you have a target date?"
}
```
**Primary event for persistence.** Client displays the transcript and sends it to backend via `POST /api/v1/voice/messages` (fire-and-forget).

### AgentThinking
```json
{ "type": "AgentThinking", "content": "..." }
```
The LLM is generating a response. Update UI to "Processing..." state.

### FunctionCallRequest
```json
{
  "type": "FunctionCallRequest",
  "id": "fc_123",
  "function_name": "submit_goal_intent",
  "input": {
    "goal_statement": "Learn Spanish",
    "timeline": "3 months"
  }
}
```
**This is how intents are extracted.** The client:
1. Forwards `function_name` + `input` to backend via `POST /api/v1/voice/intents`
2. Backend validates, routes to Orchestrator, returns result string
3. Client sends `FunctionCallResponse` back to Deepgram with the result

### AgentStartedSpeaking
```json
{
  "type": "AgentStartedSpeaking",
  "total_latency": 0.45,
  "tts_latency": 0.12,
  "ttt_latency": 0.33
}
```
Model began speaking. Update UI to "Speaking..." state.

### Audio (binary frames)
TTS audio to play on the client's speakers. Played via Web Audio API.

### AgentAudioDone
```json
{ "type": "AgentAudioDone" }
```
Model finished speaking. Transition back to "Listening..." state.

### Error
```json
{ "type": "Error", "code": "...", "message": "..." }
```
Display error to user.

---

## Audio Format

| Direction | Encoding | Sample Rate | Notes |
|-----------|----------|-------------|-------|
| User → Deepgram | linear16 (PCM) | 16000 Hz | Captured via Web Audio API ScriptProcessorNode |
| Deepgram → User | linear16 (PCM) | 16000 Hz | Played via AudioContext + BufferSource |

Raw PCM bytes — no WAV headers. Sent as binary WebSocket frames.

---

## Function Calling Details

Functions are defined in the `agent.think.functions` array of the Settings message. We use **client-side functions** (no `endpoint` field) — the client receives `FunctionCallRequest` events and processes them via the backend REST API.

### Function Definition (generated from intents.yaml by backend)

```json
{
  "name": "submit_goal_intent",
  "description": "Submit a fully extracted goal intent.",
  "parameters": {
    "type": "object",
    "properties": {
      "goal_statement": {
        "type": "string",
        "description": "The user's goal in their own words"
      },
      "timeline": {
        "type": "string",
        "description": "Target date, event, or timeframe"
      }
    },
    "required": ["goal_statement"]
  }
}
```

### Processing Flow

```
Deepgram sends FunctionCallRequest to client
    → Client receives it in the browser
    → Client calls POST /api/v1/voice/intents on backend
    → Backend looks up intent by function_name
    → Backend validates payload, routes to Orchestrator
    → Backend returns result string
    → Client sends FunctionCallResponse to Deepgram
    → Deepgram agent speaks confirmation
```

---

## Turn Detection

Deepgram handles turn detection server-side automatically:
- **UserStartedSpeaking** — user began talking (interrupts agent if speaking)
- Silence detection triggers agent response (Deepgram manages timing)
- Agent can be interrupted mid-speech naturally

No client-side VAD library needed.

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Deepgram WebSocket drops | Client retries 3 times, 2s apart. If failed: show error, end session. |
| Deepgram returns Error event | Display to user. If fatal: end session. |
| Invalid function call args | Backend returns error string → client sends as FunctionCallResponse → agent re-asks user. |
| Orchestrator failure | Backend returns error string → agent says "trouble setting up." |
| KeepAlive timeout | Deepgram closes connection. Client detects, cleans up. |

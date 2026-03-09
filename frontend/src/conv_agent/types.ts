/**
 * Flux Conv Agent -- Voice Types
 *
 * TypeScript types for the voice conversational agent.
 * Covers backend API shapes and Deepgram WebSocket event types.
 */

// -- Voice Session Status ---------------------------------------------------

export type VoiceStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "listening"
  | "speaking"
  | "error";

// -- Voice Messages (displayed in transcript) -------------------------------

export interface VoiceMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

// -- Backend API Types ------------------------------------------------------

export interface CreateSessionRequest {
  user_id: string;
}

export interface FunctionConfig {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface SessionConfig {
  system_prompt: string;
  functions: FunctionConfig[];
  voice_model: string;
  listen_model: string;
  llm_model: string;
  greeting: string;
}

export interface CreateSessionResponse {
  session_id: string;
  deepgram_token: string;
  config: SessionConfig;
}

export interface SaveMessageRequest {
  session_id: string;
  role: string;
  content: string;
}

export interface SaveMessageResponse {
  message_id: string;
  status: string;
}

export interface SubmitIntentRequest {
  session_id: string;
  function_call_id: string;
  function_name: string;
  input: Record<string, unknown>;
}

export interface IntentResultResponse {
  function_call_id: string;
  result: string;
}

export interface CloseSessionResponse {
  session_id: string;
  status: string;
  message_count: number;
}

// -- Deepgram WebSocket Event Types -----------------------------------------

/** Sent once after WebSocket opens -- connection confirmed. */
export interface DGWelcomeEvent {
  type: "Welcome";
}

/** Sent after the Settings message is accepted. */
export interface DGSettingsAppliedEvent {
  type: "SettingsApplied";
}

/** User started speaking -- interrupt agent playback. */
export interface DGUserStartedSpeakingEvent {
  type: "UserStartedSpeaking";
}

/** Transcript text from either user or assistant. */
export interface DGConversationTextEvent {
  type: "ConversationText";
  role: "user" | "assistant";
  content: string;
}

/** Agent is processing the user's input. */
export interface DGAgentThinkingEvent {
  type: "AgentThinking";
}

/** A single function entry inside a V1 FunctionCallRequest. */
export interface DGFunctionCallItem {
  id: string;
  name: string;
  /** JSON-encoded argument object, e.g. '{"goal": "lose weight"}' */
  arguments: string;
  client_side: boolean;
}

/** Deepgram agent is calling one or more registered functions (V1 format). */
export interface DGFunctionCallRequestEvent {
  type: "FunctionCallRequest";
  functions: DGFunctionCallItem[];
}

/** Agent started speaking -- TTS audio follows. */
export interface DGAgentStartedSpeakingEvent {
  type: "AgentStartedSpeaking";
}

/** Agent finished speaking all audio for this turn. */
export interface DGAgentAudioDoneEvent {
  type: "AgentAudioDone";
}

/** Union of all known Deepgram text events. */
export type DeepgramEvent =
  | DGWelcomeEvent
  | DGSettingsAppliedEvent
  | DGUserStartedSpeakingEvent
  | DGConversationTextEvent
  | DGAgentThinkingEvent
  | DGFunctionCallRequestEvent
  | DGAgentStartedSpeakingEvent
  | DGAgentAudioDoneEvent;

// -- Deepgram Settings Message ----------------------------------------------

/** The Settings message sent to Deepgram after WebSocket opens. */
export interface DeepgramSettingsMessage {
  type: "Settings";
  audio: {
    input: { encoding: string; sample_rate: number };
    output: { encoding: string; sample_rate: number; container: string };
  };
  agent: {
    language: string;
    listen: { provider: { type: string; model: string } };
    think: {
      provider: { type: string; model: string };
      prompt: string;
      functions: FunctionConfig[];
    };
    speak: { provider: { type: string; model: string } };
    greeting: string;
  };
}

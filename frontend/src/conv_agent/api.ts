/**
 * Flux Conv Agent -- Voice API Client
 *
 * REST client for the voice control-plane endpoints on the FastAPI backend.
 * All functions are async and throw on non-2xx responses.
 */

import type {
  CloseSessionResponse,
  CreateSessionResponse,
  IntentResultResponse,
  SaveMessageResponse,
} from "./types";

/** Base URL for the backend API. Reads from env or defaults to localhost. */
const API_BASE =
  typeof import.meta !== "undefined" &&
  // biome-ignore lint/suspicious/noExplicitAny: import.meta env typing
  (import.meta as any).env?.VITE_API_BASE
    ? // biome-ignore lint/suspicious/noExplicitAny: import.meta env typing
      (import.meta as any).env.VITE_API_BASE
    : "http://localhost:8000";

// -- Helpers ----------------------------------------------------------------

async function post<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`POST ${path} failed: ${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

async function _get<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`GET ${path} failed: ${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!resp.ok) {
    throw new Error(`DELETE ${path} failed: ${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

// -- Voice Endpoints --------------------------------------------------------

/** Create a new voice session -- returns token + config for Deepgram. */
export async function createVoiceSession(
  userId: string,
): Promise<CreateSessionResponse> {
  return post<CreateSessionResponse>("/api/v1/voice/session", {
    user_id: userId,
  });
}

/**
 * Save a transcript message (fire-and-forget).
 * Errors are caught internally -- this should never block the voice flow.
 */
export async function saveVoiceMessage(
  sessionId: string,
  role: string,
  content: string,
): Promise<SaveMessageResponse | null> {
  try {
    return await post<SaveMessageResponse>("/api/v1/voice/messages", {
      session_id: sessionId,
      role,
      content,
    });
  } catch (err) {
    console.warn("Failed to save voice message (non-blocking):", err);
    return null;
  }
}

/** Submit a Deepgram function-call intent to the backend for processing. */
export async function submitVoiceIntent(
  sessionId: string,
  functionCallId: string,
  functionName: string,
  input: Record<string, unknown>,
): Promise<IntentResultResponse> {
  return post<IntentResultResponse>("/api/v1/voice/intents", {
    session_id: sessionId,
    function_call_id: functionCallId,
    function_name: functionName,
    input,
  });
}

/** Close a voice session. */
export async function closeVoiceSession(
  sessionId: string,
): Promise<CloseSessionResponse> {
  return del<CloseSessionResponse>(`/api/v1/voice/session/${sessionId}`);
}

/**
 * Flux Conv Agent -- useVoiceAgent Hook
 *
 * React hook that orchestrates the full voice conversation flow:
 *   1. Creates a backend session (token + config)
 *   2. Connects to Deepgram via DeepgramClient
 *   3. Captures mic audio via AudioEngine
 *   4. Handles incoming events (transcript, function calls, TTS)
 *   5. Persists messages and routes intents to the backend
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AudioEngine } from "./AudioEngine";
import {
  closeVoiceSession,
  createVoiceSession,
  saveVoiceMessage,
  submitVoiceIntent,
} from "./api";
import { DeepgramClient } from "./DeepgramClient";
import type { DeepgramEvent, VoiceMessage, VoiceStatus } from "./types";

interface UseVoiceAgentReturn {
  status: VoiceStatus;
  messages: VoiceMessage[];
  isAgentSpeaking: boolean;
  startSession: () => Promise<void>;
  endSession: () => Promise<void>;
}

export function useVoiceAgent(userId: string): UseVoiceAgentReturn {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);

  // Refs to hold mutable instances across renders
  const dgClientRef = useRef<DeepgramClient | null>(null);
  const audioEngineRef = useRef<AudioEngine | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const messageCountRef = useRef(0);

  // -- Event Handlers -------------------------------------------------------

  /** Forward a Deepgram function call to the backend and return the result. */
  const handleFunctionCall = useCallback(
    async (
      callId: string,
      functionName: string,
      input: Record<string, unknown>,
    ) => {
      if (!sessionIdRef.current) return;

      try {
        const result = await submitVoiceIntent(
          sessionIdRef.current,
          callId,
          functionName,
          input,
        );

        // V1 FunctionCallResponse requires id, name, and content.
        dgClientRef.current?.sendFunctionResult(
          callId,
          functionName,
          result.result,
        );
      } catch (err) {
        console.error("Intent processing failed:", err);
        dgClientRef.current?.sendFunctionResult(
          callId,
          functionName,
          "Sorry, something went wrong processing that request.",
        );
      }
    },
    [],
  );

  /** Handle all text-based events from the Deepgram WebSocket. */
  const handleDeepgramEvent = useCallback(
    (event: DeepgramEvent) => {
      switch (event.type) {
        case "Welcome":
          // Connection established -- waiting for SettingsApplied
          break;

        case "SettingsApplied":
          // Config accepted -- now listening
          setStatus("listening");
          break;

        case "UserStartedSpeaking":
          // User interrupted -- stop TTS playback
          setIsAgentSpeaking(false);
          audioEngineRef.current?.stopPlayback();
          setStatus("listening");
          break;

        case "ConversationText": {
          // Add transcript message to the UI
          const msg: VoiceMessage = {
            id: `voice-${++messageCountRef.current}`,
            role: event.role,
            content: event.content,
          };
          setMessages((prev) => [...prev, msg]);

          // Fire-and-forget persist to backend
          if (sessionIdRef.current) {
            saveVoiceMessage(sessionIdRef.current, event.role, event.content);
          }
          break;
        }

        case "AgentThinking":
          setStatus("connected"); // "Processing..."
          break;

        case "FunctionCallRequest": {
          // V1 format: array of functions; handle the first client_side one.
          const fn =
            event.functions.find((f) => f.client_side) ?? event.functions[0];
          if (fn) {
            let args: Record<string, unknown> = {};
            try {
              args = JSON.parse(fn.arguments);
            } catch {
              console.warn(
                "[VoiceAgent] Could not parse function arguments:",
                fn.arguments,
              );
            }
            handleFunctionCall(fn.id, fn.name, args);
          }
          break;
        }

        case "AgentStartedSpeaking":
          setIsAgentSpeaking(true);
          setStatus("speaking");
          break;

        case "AgentAudioDone":
          setIsAgentSpeaking(false);
          setStatus("listening");
          break;
      }
    },
    [handleFunctionCall], // stable -- uses refs for mutable state
  );

  // -- Session Lifecycle ----------------------------------------------------

  /** Start a new voice session -- backend + Deepgram + mic. */
  const startSession = useCallback(async () => {
    if (status !== "idle" && status !== "error") return;

    setStatus("connecting");
    setMessages([]);
    messageCountRef.current = 0;

    try {
      // 1. Create backend session (token + config)
      const session = await createVoiceSession(userId);
      sessionIdRef.current = session.session_id;

      // 2. Initialize audio engine and start mic capture
      const audioEngine = new AudioEngine();
      audioEngineRef.current = audioEngine;

      // 3. Initialize Deepgram client with event handlers
      const dgClient = new DeepgramClient({
        onOpen: () => {
          // Settings are sent automatically in DeepgramClient.connect()
        },
        onClose: (code, reason) => {
          console.warn("[VoiceAgent] Deepgram closed:", code, reason);
          if (status !== "idle") {
            setStatus("idle");
          }
        },
        onError: (err) => {
          console.error("[VoiceAgent] Deepgram error:", err);
          setStatus("error");
        },
        onTextEvent: handleDeepgramEvent,
        onAudioData: (pcmData) => {
          audioEngine.playAudio(pcmData);
        },
      });
      dgClientRef.current = dgClient;

      // 4. Connect to Deepgram (sends Settings on open)
      dgClient.connect(session.deepgram_token, session.config);

      // 5. Start mic capture -- sends PCM audio to Deepgram
      await audioEngine.startCapture((pcmBuffer) => {
        dgClient.sendAudio(pcmBuffer);
      });

      setStatus("connected");
    } catch (err) {
      console.error("Failed to start voice session:", err);
      setStatus("error");
    }
  }, [userId, status, handleDeepgramEvent]);

  /** End the current voice session -- cleanup everything. */
  const endSession = useCallback(async () => {
    // Disconnect Deepgram
    dgClientRef.current?.disconnect();
    dgClientRef.current = null;

    // Stop audio
    audioEngineRef.current?.destroy();
    audioEngineRef.current = null;

    // Close backend session
    if (sessionIdRef.current) {
      try {
        await closeVoiceSession(sessionIdRef.current);
      } catch (err) {
        console.warn("Failed to close session on backend:", err);
      }
      sessionIdRef.current = null;
    }

    setStatus("idle");
    setIsAgentSpeaking(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      dgClientRef.current?.disconnect();
      audioEngineRef.current?.destroy();
    };
  }, []);

  return {
    status,
    messages,
    isAgentSpeaking,
    startSession,
    endSession,
  };
}

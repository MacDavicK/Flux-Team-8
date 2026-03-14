/**
 * useVoice — Deepgram push-to-talk STT hook
 *
 * State machine: idle → connecting → recording → transcribing → done → idle
 *
 * Audio flows: browser mic → Deepgram WS directly (via short-lived token
 * from GET /api/v1/voice/token). The Deepgram API key never leaves the backend.
 *
 * TTS: playTTS() fetches a short-lived Deepgram token and calls the TTS API
 * directly. No extra FastAPI proxy round-trip.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, getInMemoryToken } from "~/lib/apiClient";

type VoiceStatus =
  | "idle"
  | "connecting"
  | "recording"
  | "transcribing"
  | "done";

export interface UseVoiceReturn {
  startRecording: () => void;
  stopRecording: () => void;
  playTTS: (text: string) => Promise<void>;
  transcript: string | null;
  isConnecting: boolean;
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  reset: () => void;
  stream: MediaStream | null;
}

export function useVoice(): UseVoiceReturn {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const micDeniedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Accumulates is_final transcript fragments; cleared on each startRecording
  const accumulatedRef = useRef<string>("");
  // Ref mirrors status so WS callbacks read the current value without stale closures
  const statusRef = useRef<VoiceStatus>("idle");
  // Set to true if stopRecording is called while still connecting (async token fetch)
  const pendingStopRef = useRef(false);

  const setStatusSync = useCallback((s: VoiceStatus) => {
    statusRef.current = s;
    setStatus(s);
  }, []);

  const reset = useCallback(() => {
    pendingStopRef.current = false;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }
    wsRef.current = null;
    recorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        t.stop();
      });
      streamRef.current = null;
    }
    accumulatedRef.current = "";
    setStream(null);
    setTranscript(null);
    setError(null);
    setStatusSync("idle");
  }, [setStatusSync]);

  const stopRecording = useCallback(() => {
    // If still connecting (async token fetch in flight), flag it so
    // startRecording aborts as soon as it resumes after the await.
    if (statusRef.current === "connecting") {
      pendingStopRef.current = true;
      return;
    }

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        t.stop();
      });
      streamRef.current = null;
    }
    setStream(null);

    const wsIsOpen =
      wsRef.current && wsRef.current.readyState === WebSocket.OPEN;
    if (wsIsOpen) {
      setStatusSync("transcribing");
      wsRef.current?.send(JSON.stringify({ type: "CloseStream" }));
    } else {
      setStatusSync("idle");
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    }
  }, [setStatusSync]);

  const startRecording = useCallback(async () => {
    if (micDeniedRef.current) {
      setError("Microphone access is needed for voice input.");
      return;
    }

    reset();
    pendingStopRef.current = false;
    setStatusSync("connecting");

    // 1. Get JWT from memory (set by AuthContext on login)
    const jwtToken = getInMemoryToken();
    if (!jwtToken) {
      setError("Couldn't start voice. Try again.");
      setStatusSync("idle");
      return;
    }

    // 2. Fetch a short-lived Deepgram token from the backend
    let dgToken: string;
    try {
      const resp = await apiFetch("/api/v1/voice/token");
      if (!resp.ok) {
        setError("Couldn't start voice. Try again.");
        setStatusSync("idle");
        return;
      }
      const data = (await resp.json()) as { token: string };
      dgToken = data.token;
    } catch {
      setError("Couldn't start voice. Try again.");
      setStatusSync("idle");
      return;
    }

    // User tapped stop while token was being fetched — abort cleanly.
    if (pendingStopRef.current) {
      pendingStopRef.current = false;
      setStatusSync("idle");
      return;
    }

    // 3. Request microphone — do this after token fetch so AudioContext
    //    creation (in VoiceWaveform) stays within the same user gesture
    let mediaStream: MediaStream;
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = mediaStream;
      setStream(mediaStream);
    } catch {
      micDeniedRef.current = true;
      setError("Microphone access is needed for voice input.");
      setStatusSync("idle");
      return;
    }

    // 4. Connect directly to Deepgram STT
    //    Browser WS API cannot set custom headers. Deepgram supports
    //    authentication via the Sec-WebSocket-Protocol header:
    //      new WebSocket(url, ["bearer", "<jwt>"])
    const wsUrl =
      `wss://api.deepgram.com/v1/listen` +
      `?model=nova-3&language=en&encoding=opus&container=webm`;
    const ws = new WebSocket(wsUrl, ["bearer", dgToken]);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatusSync("recording");

      // 5. Start MediaRecorder and stream chunks directly to Deepgram
      const recorder = new MediaRecorder(mediaStream, {
        mimeType: "audio/webm;codecs=opus",
      });
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };

      recorder.start(250);

      // 60s safety guard
      timeoutRef.current = setTimeout(() => {
        stopRecording();
      }, 60_000);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string) as {
          is_final?: boolean;
          speech_final?: boolean;
          channel?: { alternatives?: Array<{ transcript?: string }> };
        };

        // Only accumulate is_final fragments — ignore speech_final auto-submit.
        // The user controls when to stop via the mic button (stopRecording).
        if (msg.is_final) {
          const text = msg.channel?.alternatives?.[0]?.transcript ?? "";
          if (text.trim()) {
            accumulatedRef.current +=
              (accumulatedRef.current ? " " : "") + text.trim();
          }
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onerror = () => {
      setError("Voice unavailable. Try again.");
      reset();
    };

    ws.onclose = () => {
      // Surface whatever we accumulated when the stream closes
      if (
        statusRef.current === "transcribing" ||
        statusRef.current === "recording"
      ) {
        if (accumulatedRef.current) {
          setTranscript(accumulatedRef.current);
          setStatusSync("done");
        } else {
          setStatusSync("idle");
        }
      }
    };
  }, [reset, stopRecording, setStatusSync]);

  const playTTS = useCallback(async (text: string) => {
    // Cancel any currently playing TTS
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    try {
      const tokenResp = await apiFetch("/api/v1/voice/token");
      if (!tokenResp.ok) return;
      const { token } = (await tokenResp.json()) as { token: string };

      const response = await fetch(
        `https://api.deepgram.com/v1/speak?model=aura-asteria-en`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text }),
        },
      );
      if (!response.ok) return;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        audioRef.current = null;
      };
      audio.play().catch(() => {});
    } catch {
      // Silent failure — text response is already visible
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      reset();
    };
  }, [reset]);

  return {
    startRecording,
    stopRecording,
    playTTS,
    transcript,
    isConnecting: status === "connecting",
    isRecording: status === "recording",
    isProcessing: status === "transcribing",
    error,
    reset,
    stream,
  };
}

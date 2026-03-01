/**
 * useVoiceNegotiation — Web Speech API wrapper for task drift negotiation.
 *
 * Provides:
 *   - speak(text): Speak a string via SpeechSynthesis
 *   - startListening(): Begin speech recognition
 *   - transcript: Current recognized text
 *   - isListening: Whether the mic is active
 *   - isSupported: Whether the browser supports both TTS and STT
 *
 * Voice command mapping:
 *   "yes" / "sure" / "do it" / "go ahead"  →  action: "accept_first"
 *   "tomorrow" / "next" / "later"           →  action: "accept_second"
 *   "skip" / "no" / "pass" / "cancel"       →  action: "skip"
 */

import { useCallback, useEffect, useRef, useState } from "react";

type VoiceAction = "accept_first" | "accept_second" | "skip" | null;

const COMMAND_MAP: Record<string, VoiceAction> = {
  // Accept first suggestion
  yes: "accept_first",
  sure: "accept_first",
  "do it": "accept_first",
  "go ahead": "accept_first",
  okay: "accept_first",
  ok: "accept_first",
  // Accept second suggestion (tomorrow)
  tomorrow: "accept_second",
  next: "accept_second",
  later: "accept_second",
  // Skip
  skip: "skip",
  no: "skip",
  pass: "skip",
  cancel: "skip",
  miss: "skip",
};

export function useVoiceNegotiation() {
  const [isSupported, setIsSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [detectedAction, setDetectedAction] = useState<VoiceAction>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Check browser support on mount
  useEffect(() => {
    const hasTTS = "speechSynthesis" in window;
    const hasSTT =
      "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
    setIsSupported(hasTTS && hasSTT);
  }, []);

  // Speak text via SpeechSynthesis
  const speak = useCallback(
    (text: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        if (!("speechSynthesis" in window)) {
          reject(new Error("SpeechSynthesis not supported"));
          return;
        }

        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.lang = "en-US";

        // Prefer a natural-sounding voice
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(
          (v) => v.name.includes("Samantha") || v.name.includes("Google"),
        );
        if (preferred) utterance.voice = preferred;

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => {
          setIsSpeaking(false);
          resolve();
        };
        utterance.onerror = (e) => {
          setIsSpeaking(false);
          reject(e);
        };

        window.speechSynthesis.speak(utterance);
      });
    },
    [],
  );

  // Start listening for voice commands
  const startListening = useCallback(() => {
    if (!isSupported) return;

    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionClass) return;
    const recognition = new SpeechRecognitionClass();

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.maxAlternatives = 3;

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
      setDetectedAction(null);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const results = event.results[0];
      const text = results[0].transcript.toLowerCase().trim();
      setTranscript(text);

      // Match against command map
      for (const [keyword, action] of Object.entries(COMMAND_MAP)) {
        if (text.includes(keyword)) {
          setDetectedAction(action);
          break;
        }
      }
    };

    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  }, [isSupported]);

  // Stop listening
  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  // Cleanup
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      window.speechSynthesis?.cancel();
    };
  }, []);

  return {
    isSupported,
    isListening,
    isSpeaking,
    transcript,
    detectedAction,
    speak,
    startListening,
    stopListening,
  };
}
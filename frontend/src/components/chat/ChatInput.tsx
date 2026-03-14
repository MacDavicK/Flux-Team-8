/**
 * Flux Frontend — ChatInput
 *
 * Text input bar for the chat page.
 * Shows a send button when text is present, or a mic button when empty
 * (to start a voice session).
 *
 * Voice state is owned by the parent (ChatPage) via useVoice and passed in
 * as the `voice` prop, so the same instance can also drive TTS playback.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { MicButton } from "~/components/chat/MicButton";
import { VoiceWaveform } from "~/components/chat/VoiceWaveform";
import type { UseVoiceReturn } from "~/hooks/useVoice";
import { cn } from "~/utils/cn";

interface ChatInputProps {
  onSend: (message: string) => void;
  onVoiceSend?: () => void;
  placeholder?: string;
  disabled?: boolean;
  voice: UseVoiceReturn;
}

export function ChatInput({
  onSend,
  onVoiceSend,
  placeholder = "What is on your mind?",
  disabled = false,
  voice,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    startRecording,
    stopRecording,
    transcript,
    isConnecting,
    isRecording,
    isProcessing,
    error,
    reset,
    stream,
  } = voice;

  useEffect(() => {
    if (!disabled) {
      inputRef.current?.focus();
    }
  }, [disabled]);

  // Consume transcript → send as message
  useEffect(() => {
    if (transcript) {
      onVoiceSend?.();
      onSend(transcript);
      reset();
    }
  }, [transcript, onSend, onVoiceSend, reset]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
      inputRef.current?.focus();
    }
  };

  const hasContent = message.length > 0;

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="px-5 pb-32 pt-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <div
        className={cn(
          "glass-bubble flex items-center gap-3 px-4 py-3 min-h-[52px]",
          "transition-shadow duration-200 !rounded-full",
          isFocused && "shadow-lg ring-2 ring-sage/20",
        )}
      >
        <Sparkles className="w-5 h-5 text-sage/50 flex-shrink-0" />

        <AnimatePresence mode="wait" initial={false}>
          {isConnecting ? (
            <motion.div
              key="connecting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex items-center gap-2 min-w-0"
            >
              <Loader2 className="w-4 h-4 text-sage animate-spin flex-shrink-0" />
              <span
                className="text-river/60 text-[15px] italic truncate"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Connecting...
              </span>
            </motion.div>
          ) : isRecording ? (
            <motion.div
              key="waveform"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex items-center gap-3 min-w-0"
            >
              <VoiceWaveform stream={stream} />
              <span
                className="text-red-400 text-[15px] italic truncate"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Listening...
              </span>
            </motion.div>
          ) : (
            <motion.input
              key="text-input"
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder={placeholder}
              disabled={disabled}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className={cn(
                "flex-1 bg-transparent border-none outline-none",
                "text-charcoal placeholder:text-river/60",
                "text-body text-[15px]",
                disabled && "opacity-50",
              )}
              style={{ fontFamily: "var(--font-display)", fontStyle: "italic" }}
            />
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {hasContent ? (
            <motion.button
              key="send"
              type="submit"
              initial={{ opacity: 0, scale: 0.5, x: -10 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.5, x: -10 }}
              whileTap={{ scale: 0.9 }}
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center",
                "bg-sage text-white transition-colors",
                "hover:bg-sage-dark active:scale-95",
              )}
              disabled={disabled}
            >
              <Send className="w-4 h-4" />
            </motion.button>
          ) : (
            <MicButton
              key="mic"
              onClick={isRecording ? stopRecording : startRecording}
              isRecording={isRecording}
              isProcessing={isConnecting || isProcessing}
              disabled={disabled}
            />
          )}
        </AnimatePresence>
      </div>

      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="mt-2 px-1 text-xs text-red-400"
          onAnimationComplete={() => {
            setTimeout(() => reset(), 3000);
          }}
        >
          {error}
        </motion.p>
      )}
    </motion.form>
  );
}

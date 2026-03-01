/**
 * Flux Frontend — ChatInput
 *
 * Text input bar for the chat page.
 * Shows a send button when text is present, or a mic button when empty
 * (to start a voice session).
 */

import { AnimatePresence, motion } from "framer-motion";
import { Send, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { VoiceFAB } from "~/conv_agent/components/VoiceFAB";
import type { VoiceStatus } from "~/conv_agent/types";
import { cn } from "~/utils/cn";

interface ChatInputProps {
  onSend: (message: string) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Current voice session status — controls VoiceFAB appearance. */
  voiceStatus?: VoiceStatus;
  /** Called when the mic button is tapped. */
  onVoiceToggle?: () => void;
}

export function ChatInput({
  onSend,
  placeholder = "What is on your mind?",
  disabled = false,
  voiceStatus = "idle",
  onVoiceToggle,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) {
      inputRef.current?.focus();
    }
  }, [disabled]);

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
      className="px-5 pb-24 pt-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <div
        className={cn(
          "glass-bubble flex items-center gap-3 px-4 py-3 min-h-[52px]",
          "transition-shadow duration-200",
          isFocused && "shadow-lg ring-2 ring-sage/20",
        )}
      >
        <Sparkles className="w-5 h-5 text-sage/50 flex-shrink-0" />

        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            "flex-1 bg-transparent border-none outline-none",
            "text-charcoal placeholder:text-river/60",
            "text-body text-[15px]",
            disabled && "opacity-50",
          )}
          style={{ fontFamily: "var(--font-display)", fontStyle: "italic" }}
        />

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
          ) : onVoiceToggle ? (
            <motion.div
              key="mic"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
            >
              <VoiceFAB
                status={voiceStatus}
                onClick={onVoiceToggle}
                disabled={disabled}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </motion.form>
  );
}

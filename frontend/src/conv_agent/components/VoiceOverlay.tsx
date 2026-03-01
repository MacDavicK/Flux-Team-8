/**
 * Flux Conv Agent -- VoiceOverlay
 *
 * Full-screen overlay shown during an active voice session.
 * Layout:
 *   - Top:    scrollable transcript feed (reuses ChatBubble)
 *   - Bottom: status label + pulsing orb + end-call button
 */

import { AnimatePresence, motion } from "framer-motion";
import { PhoneOff } from "lucide-react";
import { useEffect, useRef } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { MessageVariant } from "~/types/message";
import { cn } from "~/utils/cn";
import type { VoiceMessage, VoiceStatus } from "../types";

interface VoiceOverlayProps {
  status: VoiceStatus;
  messages: VoiceMessage[];
  isAgentSpeaking: boolean;
  onEndSession: () => void;
}

/** Map status to a human-readable label. */
function getStatusLabel(status: VoiceStatus, isAgentSpeaking: boolean): string {
  if (isAgentSpeaking) return "Flux is speaking...";
  switch (status) {
    case "connecting":
      return "Connecting...";
    case "connected":
      return "Processing...";
    case "listening":
      return "Listening...";
    case "speaking":
      return "Flux is speaking...";
    case "error":
      return "Connection lost";
    default:
      return "";
  }
}

/** Orb color based on voice status. */
function getOrbColor(status: VoiceStatus, isAgentSpeaking: boolean): string {
  if (isAgentSpeaking || status === "speaking") return "bg-terracotta";
  if (status === "listening") return "bg-sage";
  if (status === "connecting" || status === "connected") return "bg-sage/60";
  if (status === "error") return "bg-red-400";
  return "bg-charcoal/30";
}

export function VoiceOverlay({
  status,
  messages,
  isAgentSpeaking,
  onEndSession,
}: VoiceOverlayProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const statusLabel = getStatusLabel(status, isAgentSpeaking);
  const orbColor = getOrbColor(status, isAgentSpeaking);
  const isOrbPulsing =
    status === "listening" || status === "speaking" || isAgentSpeaking;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex flex-col bg-charcoal/95 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* -- Transcript Feed ------------------------------------------------- */}
      <div className="flex-1 overflow-y-auto px-4 pt-12 pb-4">
        <AnimatePresence mode="popLayout">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              className={cn(
                "mb-3",
                msg.role === "user" ? "flex justify-end" : "",
              )}
            >
              <ChatBubble
                variant={
                  msg.role === "user" ? MessageVariant.USER : MessageVariant.AI
                }
                animate={false}
              >
                {msg.content}
              </ChatBubble>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={scrollRef} />
      </div>

      {/* -- Bottom Controls ------------------------------------------------- */}
      <div className="flex flex-col items-center gap-4 pb-12 pt-4">
        {/* Status label */}
        <p className="text-white/70 text-sm font-medium">{statusLabel}</p>

        {/* Pulsing orb */}
        <motion.div
          className={cn("w-16 h-16 rounded-full", orbColor)}
          animate={
            isOrbPulsing
              ? { scale: [1, 1.15, 1], opacity: [0.8, 1, 0.8] }
              : { scale: 1, opacity: 0.6 }
          }
          transition={
            isOrbPulsing
              ? {
                  duration: 1.5,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }
              : { duration: 0.3 }
          }
        />

        {/* End call button */}
        <motion.button
          type="button"
          onClick={onEndSession}
          className={cn(
            "w-14 h-14 rounded-full flex items-center justify-center",
            "bg-red-500 text-white shadow-lg",
            "hover:bg-red-600 active:scale-95 transition-colors",
          )}
          whileTap={{ scale: 0.9 }}
          aria-label="End voice session"
        >
          <PhoneOff className="w-6 h-6" />
        </motion.button>
      </div>
    </motion.div>
  );
}

/**
 * Flux Conv Agent -- VoiceFAB (Floating Action Button)
 *
 * Mic button displayed in the ChatInput area when the text field is empty.
 * Visual states:
 *   - idle:        gray mic icon
 *   - connecting:  pulsing sage
 *   - listening:   steady sage glow
 *   - speaking:    animated terracotta (agent talking)
 *   - error:       red with retry affordance
 */

import { motion } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import type { VoiceStatus } from "../types";
import { cn } from "~/utils/cn";

interface VoiceFABProps {
  status: VoiceStatus;
  onClick: () => void;
  disabled?: boolean;
}

/** Map voice status to visual styling. */
function getStatusStyles(status: VoiceStatus) {
  switch (status) {
    case "idle":
      return {
        bg: "bg-charcoal/20",
        ring: "",
        iconColor: "text-charcoal/60",
      };
    case "connecting":
      return {
        bg: "bg-sage/30",
        ring: "ring-2 ring-sage/40",
        iconColor: "text-sage",
      };
    case "connected":
    case "listening":
      return {
        bg: "bg-sage/20",
        ring: "ring-2 ring-sage/60 shadow-sage/20 shadow-lg",
        iconColor: "text-sage",
      };
    case "speaking":
      return {
        bg: "bg-terracotta/20",
        ring: "ring-2 ring-terracotta/60 shadow-terracotta/20 shadow-lg",
        iconColor: "text-terracotta",
      };
    case "error":
      return {
        bg: "bg-red-100",
        ring: "ring-2 ring-red-400",
        iconColor: "text-red-500",
      };
    default:
      return { bg: "bg-charcoal/20", ring: "", iconColor: "text-charcoal/60" };
  }
}

export function VoiceFAB({ status, onClick, disabled = false }: VoiceFABProps) {
  const styles = getStatusStyles(status);
  const isActive = status !== "idle" && status !== "error";
  const isPulsing = status === "connecting";

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "w-10 h-10 rounded-full flex items-center justify-center",
        "transition-all duration-300",
        styles.bg,
        styles.ring,
        disabled && "opacity-50 cursor-not-allowed",
      )}
      whileTap={{ scale: 0.9 }}
      animate={
        isPulsing
          ? { scale: [1, 1.1, 1], opacity: [0.7, 1, 0.7] }
          : { scale: 1, opacity: 1 }
      }
      transition={
        isPulsing
          ? { duration: 1.2, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }
          : { duration: 0.2 }
      }
      aria-label={isActive ? "End voice session" : "Start voice session"}
    >
      {status === "error" ? (
        <MicOff className={cn("w-5 h-5", styles.iconColor)} />
      ) : (
        <Mic className={cn("w-5 h-5", styles.iconColor)} />
      )}
    </motion.button>
  );
}

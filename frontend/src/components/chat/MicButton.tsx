import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Mic, MicOff } from "lucide-react";
import { cn } from "~/utils/cn";

interface MicButtonProps {
  onClick: () => void;
  isRecording: boolean;
  isProcessing: boolean;
  disabled?: boolean;
}

export function MicButton({
  onClick,
  isRecording,
  isProcessing,
  disabled = false,
}: MicButtonProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.button
        key={isRecording ? "recording" : isProcessing ? "processing" : "idle"}
        type="button"
        onClick={onClick}
        initial={{ opacity: 0, scale: 0.5, x: -10 }}
        animate={{ opacity: 1, scale: 1, x: 0 }}
        exit={{ opacity: 0, scale: 0.5, x: -10 }}
        whileTap={{ scale: 0.9 }}
        disabled={disabled || isProcessing}
        className={cn(
          "w-9 h-9 rounded-full flex items-center justify-center transition-colors",
          isRecording
            ? "bg-red-500 text-white"
            : isProcessing
              ? "bg-sage/30 text-sage"
              : "bg-sage/15 text-sage hover:bg-sage/25",
        )}
      >
        {isProcessing ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isRecording ? (
          <MicOff className="w-4 h-4" />
        ) : (
          <Mic className="w-[18px] h-[18px]" />
        )}
      </motion.button>
    </AnimatePresence>
  );
}

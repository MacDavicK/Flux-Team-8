import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface CurrentTimeLineProps {
  time?: string;
}

export function CurrentTimeLine({ time }: CurrentTimeLineProps) {
  const currentTime =
    time ||
    new Date().toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });

  return (
    <motion.div
      className="relative flex items-center gap-3 py-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5 }}
    >
      {/* "Now" Label */}
      <motion.span
        className="text-sage font-semibold text-sm whitespace-nowrap"
        style={{ fontFamily: "var(--font-body)" }}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.6 }}
      >
        Now
      </motion.span>

      {/* Frosted glass line */}
      <div
        className="flex-1 h-px relative"
        style={{
          background:
            "linear-gradient(90deg, rgba(92, 124, 102, 0.4) 0%, rgba(92, 124, 102, 0.1) 100%)",
        }}
      >
        {/* Glow effect */}
        <div
          className="absolute inset-0 blur-sm"
          style={{
            background:
              "linear-gradient(90deg, rgba(92, 124, 102, 0.3) 0%, transparent 50%)",
          }}
        />
      </div>

      {/* Time */}
      <motion.span
        className="text-river text-sm whitespace-nowrap"
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.7 }}
      >
        {currentTime}
      </motion.span>
    </motion.div>
  );
}

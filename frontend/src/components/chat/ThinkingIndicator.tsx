import { motion } from "framer-motion";

interface ThinkingIndicatorProps {
  label?: string;
}

export function ThinkingIndicator({ label }: ThinkingIndicatorProps) {
  return (
    <div className="flex items-center gap-2 py-4 px-2">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-sage/60"
            animate={{
              y: [0, -8, 0],
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              delay: i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
      {label && (
        <span className="text-sm text-muted-foreground italic">{label}</span>
      )}
    </div>
  );
}

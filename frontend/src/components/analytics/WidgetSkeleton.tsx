import { motion } from "framer-motion";

interface WidgetSkeletonProps {
  className?: string;
  lines?: number;
}

export function WidgetSkeleton({
  className = "",
  lines = 3,
}: WidgetSkeletonProps) {
  return (
    <motion.div
      className={`glass-card p-4 ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{
        duration: 2,
        ease: "easeInOut",
        repeat: Infinity,
      }}
    >
      <div className="space-y-3">
        <div className="h-5 w-24 rounded bg-sage/30" />
        {Array.from({ length: lines }, (_, i) => (
          <div
            className="h-4 rounded bg-sage/20"
            // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton lines, order fixed
            key={i}
            style={{ width: `${80 - i * 15}%` }}
          />
        ))}
      </div>
    </motion.div>
  );
}

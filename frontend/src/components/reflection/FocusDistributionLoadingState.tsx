import { motion } from "framer-motion";

export function FocusDistributionLoadingState() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
        Focus Distribution
      </h3>

      <div className="glass-card p-6">
        <motion.div
          className="relative h-40 flex items-center justify-center"
          animate={{
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        >
          {[1, 2, 3].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{
                width: 80,
                height: 80,
                backgroundColor: "rgba(92, 124, 102, 0.3)",
                left: `calc(50% - 40px + ${(i - 2) * 20}px)`,
                top: `calc(50% - 40px + ${(i - 2) * 15}px)`,
              }}
              animate={{
                scale: [1, 1.05, 1],
              }}
              transition={{
                duration: 2,
                ease: "easeInOut",
                repeat: Infinity,
                delay: i * 0.3,
              }}
            />
          ))}
        </motion.div>

        <div className="flex justify-center gap-4 mt-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-sage/30" />
              <div className="h-3 w-16 rounded bg-sage/30" />
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

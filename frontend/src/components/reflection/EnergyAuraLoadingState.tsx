import { motion } from "framer-motion";

export function EnergyAuraLoadingState() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
        Energy Aura
      </h3>
      <div className="glass-card p-4 overflow-hidden">
        <motion.div
          className="w-full h-32 flex items-center justify-center"
          animate={{
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        >
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="w-8 h-8 rounded-full bg-sage/30"
                animate={{
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  duration: 1.5,
                  ease: "easeInOut",
                  repeat: Infinity,
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

import { motion } from "framer-motion";

export function StatsLoadingState() {
  return (
    <motion.div
      className="grid grid-cols-3 gap-3"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="glass-card p-4 flex flex-col items-center gap-2"
          animate={{
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
            repeat: Infinity,
            delay: i * 0.2,
          }}
        >
          <div className="w-5 h-5 rounded-full bg-sage/30" />
          <div className="h-4 w-12 rounded bg-sage/30" />
          <div className="h-3 w-8 rounded bg-sage/30" />
        </motion.div>
      ))}
    </motion.div>
  );
}

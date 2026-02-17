import { motion } from "framer-motion";

export function WeeklyInsightLoadingState() {
  return (
    <motion.div
      className="glass-card p-5"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <motion.div
        className="h-5 w-32 rounded bg-sage/30 mb-2"
        animate={{
          opacity: [0.5, 1, 0.5],
        }}
        transition={{
          duration: 2,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />
      <motion.div
        className="space-y-2"
        animate={{
          opacity: [0.3, 0.6, 0.3],
        }}
        transition={{
          duration: 2,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      >
        <div className="h-3 w-full rounded bg-sage/30" />
        <div className="h-3 w-full rounded bg-sage/30" />
        <div className="h-3 w-4/5 rounded bg-sage/30" />
      </motion.div>
    </motion.div>
  );
}

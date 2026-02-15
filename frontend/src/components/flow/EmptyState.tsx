import { motion } from "framer-motion";

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = "Open space for clarity.",
}: EmptyStateProps) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-20 px-8"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6 }}
    >
      {/* Breathing orb */}
      <motion.div
        className="relative w-32 h-32 mb-6"
        animate={{
          scale: [1, 1.05, 1],
          opacity: [0.7, 1, 0.7],
        }}
        transition={{
          duration: 4,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      >
        {/* Outer glow */}
        <div
          className="absolute inset-0 rounded-full blur-xl"
          style={{
            background:
              "radial-gradient(circle, rgba(92, 124, 102, 0.3) 0%, transparent 70%)",
          }}
        />

        {/* Inner orb */}
        <div
          className="absolute inset-4 rounded-full"
          style={{
            background:
              "radial-gradient(circle at 30% 30%, rgba(212, 217, 210, 0.9) 0%, rgba(92, 124, 102, 0.3) 100%)",
            boxShadow: "inset 0 0 20px rgba(255, 255, 255, 0.5)",
          }}
        />
      </motion.div>

      {/* Message */}
      <motion.p
        className="text-display italic text-xl text-charcoal/70 text-center"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        {message}
      </motion.p>
    </motion.div>
  );
}

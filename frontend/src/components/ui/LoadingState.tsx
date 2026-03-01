import { motion } from "framer-motion";
import { GlassCard } from "./GlassCard";

export function LoadingState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-8">
      {/* Loading Orb */}
      <motion.div
        className="relative w-40 h-40 mb-8"
        animate={{
          scale: [1, 1.08, 1],
          opacity: [0.8, 1, 0.8],
        }}
        transition={{
          duration: 3,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      >
        {/* Outer glow */}
        <motion.div
          className="absolute inset-0 rounded-full blur-2xl"
          animate={{
            opacity: [0.4, 0.7, 0.4],
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
            repeat: Infinity,
          }}
          style={{
            background:
              "radial-gradient(circle, rgba(92, 124, 102, 0.4) 0%, transparent 70%)",
          }}
        />

        {/* Middle glow */}
        <motion.div
          className="absolute inset-2 rounded-full blur-xl"
          animate={{
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 2.5,
            ease: "easeInOut",
            repeat: Infinity,
            delay: 0.3,
          }}
          style={{
            background:
              "radial-gradient(circle, rgba(194, 125, 102, 0.35) 0%, transparent 60%)",
          }}
        />

        {/* Inner orb */}
        <div
          className="absolute inset-4 rounded-full"
          style={{
            background:
              "radial-gradient(circle at 30% 30%, rgba(212, 217, 210, 0.95) 0%, rgba(92, 124, 102, 0.4) 100%)",
            boxShadow: "inset 0 0 30px rgba(255, 255, 255, 0.6)",
          }}
        />

        {/* Floating particles */}
        <motion.div
          className="absolute w-2 h-2 rounded-full bg-sage/60"
          style={{
            top: "20%",
            left: "10%",
          }}
          animate={{
            y: [-5, 5, -5],
            opacity: [0.4, 0.8, 0.4],
          }}
          transition={{
            duration: 2,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        />
        <motion.div
          className="absolute w-2 h-2 rounded-full bg-sage/60"
          style={{
            top: "45%",
            left: "45%",
          }}
          animate={{
            y: [-5, 5, -5],
            opacity: [0.4, 0.8, 0.4],
          }}
          transition={{
            duration: 2.5,
            ease: "easeInOut",
            repeat: Infinity,
            delay: 0.3,
          }}
        />
        <motion.div
          className="absolute w-2 h-2 rounded-full bg-sage/60"
          style={{
            top: "70%",
            left: "80%",
          }}
          animate={{
            y: [-5, 5, -5],
            opacity: [0.4, 0.8, 0.4],
          }}
          transition={{
            duration: 3,
            ease: "easeInOut",
            repeat: Infinity,
            delay: 0.6,
          }}
        />
      </motion.div>

      {/* Loading Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <GlassCard
          variant="bubble"
          className="px-8 py-6 flex flex-col items-center"
        >
          {/* Loading text */}
          <motion.p
            className="text-display italic text-lg text-charcoal/80 mb-4"
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{
              duration: 2,
              ease: "easeInOut",
              repeat: Infinity,
            }}
          >
            Loading your flow...
          </motion.p>

          {/* Progress dots */}
          <div className="flex gap-2">
            <motion.div
              className="w-2 h-2 rounded-full bg-sage"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 1.2,
                ease: "easeInOut",
                repeat: Infinity,
              }}
            />
            <motion.div
              className="w-2 h-2 rounded-full bg-sage"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 1.2,
                ease: "easeInOut",
                repeat: Infinity,
                delay: 0.2,
              }}
            />
            <motion.div
              className="w-2 h-2 rounded-full bg-sage"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 1.2,
                ease: "easeInOut",
                repeat: Infinity,
                delay: 0.4,
              }}
            />
          </div>
        </GlassCard>
      </motion.div>

      {/* Subtle tagline */}
      <motion.p
        className="mt-6 text-sm text-charcoal/50 text-center italic"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        Gathering your moments...
      </motion.p>
    </div>
  );
}

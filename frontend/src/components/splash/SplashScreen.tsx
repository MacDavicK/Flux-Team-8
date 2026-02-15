import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

interface SplashScreenProps {
  onComplete?: () => void;
  minDuration?: number;
}

export function SplashScreen({
  onComplete,
  minDuration = 2500,
}: SplashScreenProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      onComplete?.();
    }, minDuration);

    return () => clearTimeout(timer);
  }, [minDuration, onComplete]);

  return (
    <AnimatePresence onExitComplete={() => setIsVisible(false)}>
      {isVisible && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center overflow-hidden"
        >
          <div className="absolute inset-0 bg-splash-gradient z-0" />

          <DriftingOrb
            color="bg-terracotta"
            opacity={0.2}
            size="30vh"
            initialPosition={{ top: "-10%", left: "-10%" }}
            animationName="drift-1"
          />
          <DriftingOrb
            color="bg-sage"
            opacity={0.1}
            size="40vh"
            initialPosition={{ bottom: "-10%", right: "-10%" }}
            animationName="drift-2"
          />
          <DriftingOrb
            color="bg-stone-dark"
            opacity={0.25}
            size="25vh"
            initialPosition={{ top: "40%", left: "-20%" }}
            animationName="drift-3"
          />
          <DriftingOrb
            color="bg-sage"
            opacity={0.05}
            size="20vh"
            initialPosition={{ top: "20%", right: "10%" }}
            animationName="pulse-glow"
          />

          <div className="relative z-10 flex flex-col items-center justify-center w-full max-w-md px-6 h-full">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 1.2, ease: "easeOut" }}
              className="relative w-64 h-64 flex items-center justify-center"
            >
              <div className="absolute inset-0 rounded-full bg-sage/10 blur-3xl transform scale-110" />

              <motion.div
                animate={{
                  scale: [1, 1.08, 1],
                }}
                transition={{
                  duration: 4,
                  ease: "easeInOut",
                  repeat: Infinity,
                }}
                className="w-full h-full rounded-full glass-pebble-splash flex items-center justify-center relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-white/20 to-transparent opacity-50 rounded-full" />

                <motion.h1
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5, duration: 0.8 }}
                  className="font-display italic text-5xl text-white/90 tracking-wide z-20 mix-blend-overlay drop-shadow-lg"
                >
                  Flux
                </motion.h1>
              </motion.div>

              <svg
                className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none opacity-20"
                viewBox="0 0 100 100"
                aria-hidden="true"
              >
                <title>Loading ring</title>
                <circle
                  className="text-white"
                  cx="50"
                  cy="50"
                  fill="none"
                  r="48"
                  stroke="currentColor"
                  strokeDasharray="300"
                  strokeWidth="0.5"
                  style={{
                    animation: "dash 8s linear infinite",
                  }}
                />
              </svg>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.6 }}
              transition={{ delay: 1, duration: 0.5 }}
              className="mt-16 text-center space-y-2 animate-pulse"
            >
              <p className="text-sm font-light tracking-[0.2em] uppercase text-white/80">
                Initializing Space
              </p>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="absolute bottom-8 text-center w-full z-10"
          >
            <p className="text-[10px] text-white/20 font-body tracking-widest">
              V 2.0.1
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface DriftingOrbProps {
  color: string;
  opacity: number;
  size: string;
  initialPosition: Record<string, string>;
  animationName: string;
}

function DriftingOrb({
  color,
  opacity,
  size,
  initialPosition,
  animationName,
}: DriftingOrbProps) {
  return (
    <div
      className={`absolute ${size} ${size} rounded-full ${color} orb-blur animate-${animationName}`}
      style={{
        ...initialPosition,
        opacity,
      }}
    />
  );
}

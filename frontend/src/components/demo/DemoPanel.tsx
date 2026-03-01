import { AnimatePresence, motion } from "framer-motion";
import { Clock, Home, Navigation, Plane } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

interface DemoPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onTimeWarp: () => void;
  onTravelMode: () => void;
  onSimulateLeavingHome?: () => void;
  onSimulateNearStore?: () => void;
  onEscalationSpeedChange?: (speed: number) => void;
}

export function DemoPanel({
  isOpen,
  onClose,
  onTimeWarp,
  onTravelMode,
  onSimulateLeavingHome,
  onSimulateNearStore,
  onEscalationSpeedChange,
}: DemoPanelProps) {
  const [isTravelModeActive, setIsTravelModeActive] = useState(false);
  const [escalationSpeed, setEscalationSpeed] = useState(1);

  const handleTravelModeClick = () => {
    setIsTravelModeActive(!isTravelModeActive);
    onTravelMode();
  };

  const handleSpeedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const speed = Number.parseInt(e.target.value, 10);
    setEscalationSpeed(speed);
    onEscalationSpeedChange?.(speed);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-charcoal/20 z-40"
            style={{ backdropFilter: "blur(4px)" }}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed right-0 top-1/2 -translate-y-1/2 z-50 flex"
          >
            <div className="glass-card p-3 mr-4 flex flex-col gap-2 min-w-[180px]">
              <div className="px-2 py-1 text-[10px] font-bold text-charcoal/40 uppercase tracking-widest">
                Demo Controls
              </div>

              <button
                type="button"
                onClick={onTimeWarp}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-bubble transition-all",
                  "bg-sage/10 hover:bg-sage/20 text-charcoal text-sm font-medium",
                )}
              >
                <Clock className="w-4 h-4 text-sage" />
                Time Warp
              </button>

              <button
                type="button"
                onClick={handleTravelModeClick}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-bubble transition-all",
                  isTravelModeActive
                    ? "bg-terracotta text-white shadow-lg shadow-terracotta/20"
                    : "bg-terracotta/10 hover:bg-terracotta/20 text-charcoal",
                  "text-sm font-medium",
                )}
              >
                <Plane
                  className={cn(
                    "w-4 h-4",
                    isTravelModeActive ? "text-white" : "text-terracotta",
                  )}
                />
                Travel Mode
              </button>

              <AnimatePresence>
                {isTravelModeActive && (
                  <motion.div
                    initial={{ height: 0, opacity: 0, marginTop: 0 }}
                    animate={{ height: "auto", opacity: 1, marginTop: 8 }}
                    exit={{ height: 0, opacity: 0, marginTop: 0 }}
                    className="flex flex-col gap-2 overflow-hidden border-t border-charcoal/5 pt-3"
                  >
                    <div className="px-2 pb-1 text-[9px] font-bold text-charcoal/40 uppercase tracking-tight">
                      Simulations
                    </div>

                    <button
                      type="button"
                      onClick={onSimulateLeavingHome}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl bg-charcoal/5 hover:bg-charcoal/10 text-charcoal text-xs font-medium transition-colors"
                    >
                      <Home className="w-3.5 h-3.5 text-river" />
                      Leaving Home
                    </button>

                    <button
                      type="button"
                      onClick={onSimulateNearStore}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl bg-charcoal/5 hover:bg-charcoal/10 text-charcoal text-xs font-medium transition-colors"
                    >
                      <Navigation className="w-3.5 h-3.5 text-sage" />
                      Near Store
                    </button>

                    <div className="mt-2 px-2 flex flex-col gap-2">
                      <div className="flex justify-between items-center text-[9px] font-bold text-charcoal/40 uppercase">
                        <span>Escalation Speed</span>
                        <span className="text-terracotta">
                          {escalationSpeed}x
                        </span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        step="1"
                        value={escalationSpeed}
                        onChange={handleSpeedChange}
                        className="w-full h-1 bg-charcoal/10 rounded-lg appearance-none cursor-pointer accent-terracotta"
                      />
                      <div className="flex justify-between text-[8px] text-charcoal/30 font-medium">
                        <span>Real-time</span>
                        <span>Fast</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

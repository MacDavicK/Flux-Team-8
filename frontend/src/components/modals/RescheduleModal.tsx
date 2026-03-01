import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { cn } from "~/utils/cn";
import {
  applyReschedule,
  fetchSuggestions,
  type SuggestResponse,
} from "~/utils/api";

interface RescheduleModalProps {
  isOpen: boolean;
  eventId: string;
  taskTitle: string;
  onClose: () => void;
  onRescheduleDone: () => void;
}

export function RescheduleModal({
  isOpen,
  eventId,
  taskTitle,
  onClose,
  onRescheduleDone,
}: RescheduleModalProps) {
  const [data, setData] = useState<SuggestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  const loadSuggestions = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await fetchSuggestions(eventId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load suggestions");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    if (isOpen && eventId) loadSuggestions();
  }, [isOpen, eventId, loadSuggestions]);

  const handleReschedule = async (newStart: string, newEnd: string) => {
    setApplying(true);
    try {
      await applyReschedule(eventId, "reschedule", newStart, newEnd);
      onRescheduleDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply");
    } finally {
      setApplying(false);
    }
  };

  const handleSkip = async () => {
    setApplying(true);
    try {
      await applyReschedule(eventId, "skip");
      onRescheduleDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to skip");
    } finally {
      setApplying(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-charcoal/30 z-50"
            style={{ backdropFilter: "blur(8px)" }}
          />

          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 z-50"
          >
            <div className="glass-card rounded-b-none p-6 pb-safe">
              <button
                type="button"
                onClick={onClose}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-charcoal/10 transition-colors"
              >
                <X className="w-5 h-5 text-charcoal" />
              </button>

              <div className="mb-6 pr-8">
                <p className="text-river text-sm mb-2">Reschedule</p>
                <div
                  className={cn(
                    "glass-bubble p-4 transform -rotate-1",
                    "border-l-4 border-l-terracotta",
                  )}
                >
                  <p className="text-charcoal font-medium">{taskTitle}</p>
                </div>
              </div>

              {loading && (
                <div className="space-y-3 animate-pulse">
                  <div className="h-4 bg-charcoal/10 rounded w-3/4" />
                  <div className="h-16 bg-charcoal/10 rounded" />
                  <div className="h-16 bg-charcoal/10 rounded" />
                </div>
              )}

              {error && (
                <p className="text-terracotta text-sm mb-4">{error}</p>
              )}

              {!loading && data && (
                <>
                  <p className="text-charcoal text-sm mb-4">{data.ai_message}</p>
                  <div className="space-y-3">
                    {data.suggestions.map((s, i) => (
                      <motion.button
                        key={i}
                        type="button"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        disabled={applying}
                        onClick={() =>
                          handleReschedule(s.new_start, s.new_end)
                        }
                        className={cn(
                          "w-full glass-bubble p-4 text-left flex flex-col gap-1",
                          "hover:bg-charcoal/5 transition-colors",
                          applying && "opacity-60 pointer-events-none",
                        )}
                      >
                        <span className="text-charcoal font-medium">
                          {s.label}
                        </span>
                        <span className="text-river text-xs">
                          {s.rationale}
                        </span>
                      </motion.button>
                    ))}
                    {data.skip_option && (
                      <motion.button
                        type="button"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: data.suggestions.length * 0.05 }}
                        disabled={applying}
                        onClick={handleSkip}
                        className={cn(
                          "w-full glass-bubble p-3 text-center text-river text-sm border border-river/20",
                          "hover:bg-charcoal/5 transition-colors",
                          applying && "opacity-60 pointer-events-none",
                        )}
                      >
                        Skip Today
                      </motion.button>
                    )}
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

import { AnimatePresence, motion } from "framer-motion";
import {
  Clock,
  Loader2,
  Mic,
  SkipForward,
  Sun,
  X,
  AlertCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "~/utils/cn";
import {
  fetchSuggestions,
  applyReschedule,
  type RescheduleSuggestion,
  type SchedulerSuggestResponse,
} from "~/utils/api";
import { useVoiceNegotiation } from "~/utils/useVoiceNegotiation";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

interface NegotiationModalProps {
  isOpen: boolean;
  onClose: () => void;
  eventId: string;
  taskTitle: string;
  onReschedule: (result: {
    action: string;
    newState: string;
    message: string;
    newStart?: string;
    newEnd?: string;
  }) => void;
  useVoice?: boolean;
}

// Mock data for development without backend
const MOCK_RESPONSE: SchedulerSuggestResponse = {
  event_id: "mock-1",
  task_title: "Gym Session",
  suggestions: [
    {
      new_start: new Date(Date.now() + 3 * 3600000).toISOString(),
      new_end: new Date(Date.now() + 4 * 3600000).toISOString(),
      label: "5:00 PM Today",
      rationale: "Suggested 5 PM — it's your next free slot today.",
    },
    {
      new_start: new Date(Date.now() + 18 * 3600000).toISOString(),
      new_end: new Date(Date.now() + 19 * 3600000).toISOString(),
      label: "7:00 AM Tomorrow",
      rationale: "Same time as originally planned.",
    },
  ],
  skip_option: true,
  ai_message: "Gym Session drifted. I can do:",
};

type ModalState = "loading" | "ready" | "applying" | "error";

const VOICE_LISTEN_TIMEOUT_MS = 5000;

export function NegotiationModal({
  isOpen,
  onClose,
  eventId,
  taskTitle,
  onReschedule,
  useVoice = true,
}: NegotiationModalProps) {
  const [modalState, setModalState] = useState<ModalState>("loading");
  const [data, setData] = useState<SchedulerSuggestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const voiceListenTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const voiceActionHandledRef = useRef(false);

  const {
    isSupported: isVoiceSupported,
    isListening,
    isSpeaking,
    detectedAction,
    speak,
    startListening,
    stopListening,
  } = useVoiceNegotiation();

  // Fetch suggestions when modal opens
  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes
      setModalState("loading");
      setData(null);
      setError(null);
      setApplyingId(null);
      return;
    }

    const loadSuggestions = async () => {
      setModalState("loading");
      try {
        if (USE_MOCK) {
          // Simulate network delay
          await new Promise((r) => setTimeout(r, 800));
          setData({ ...MOCK_RESPONSE, event_id: eventId, task_title: taskTitle });
        } else {
          const result = await fetchSuggestions(eventId);
          setData(result);
        }
        setModalState("ready");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load suggestions",
        );
        setModalState("error");
      }
    };

    loadSuggestions();
  }, [isOpen, eventId, taskTitle]);

  // Voice: speak AI message then start listening when ready (with 5s timeout)
  useEffect(() => {
    if (modalState !== "ready" || !data || !useVoice || !isVoiceSupported) {
      return;
    }
    voiceActionHandledRef.current = false;
    let cancelled = false;
    speak(data.ai_message)
      .then(() => {
        if (!cancelled) startListening();
      })
      .catch(() => {});

    voiceListenTimeoutRef.current = setTimeout(() => {
      if (!cancelled) stopListening();
    }, VOICE_LISTEN_TIMEOUT_MS);

    return () => {
      cancelled = true;
      if (voiceListenTimeoutRef.current) {
        clearTimeout(voiceListenTimeoutRef.current);
        voiceListenTimeoutRef.current = null;
      }
      stopListening();
    };
  }, [
    modalState,
    data,
    useVoice,
    isVoiceSupported,
    speak,
    startListening,
    stopListening,
  ]);

  // Voice: react to detected action and trigger corresponding handler
  useEffect(() => {
    if (
      !detectedAction ||
      modalState !== "ready" ||
      !data ||
      voiceActionHandledRef.current
    ) {
      return;
    }
    voiceActionHandledRef.current = true;
    if (voiceListenTimeoutRef.current) {
      clearTimeout(voiceListenTimeoutRef.current);
      voiceListenTimeoutRef.current = null;
    }
    stopListening();

    if (detectedAction === "accept_first" && data.suggestions[0]) {
      void handleSuggestionClick(data.suggestions[0]);
    } else if (detectedAction === "accept_second" && data.suggestions[1]) {
      void handleSuggestionClick(data.suggestions[1]);
    } else if (detectedAction === "skip" && data.skip_option) {
      void handleSkip();
    }
  }, [detectedAction, modalState, data, stopListening]);

  const handleSuggestionClick = async (suggestion: RescheduleSuggestion) => {
    setApplyingId(suggestion.label);
    setModalState("applying");
    try {
      if (USE_MOCK) {
        await new Promise((r) => setTimeout(r, 500));
        onReschedule({
          action: "reschedule",
          newState: "scheduled",
          message: `Done! Moved to ${suggestion.label}. You've got this!`,
          newStart: suggestion.new_start,
          newEnd: suggestion.new_end,
        });
      } else {
        const result = await applyReschedule({
          event_id: eventId,
          action: "reschedule",
          new_start: suggestion.new_start,
          new_end: suggestion.new_end,
        });
        onReschedule({
          action: result.action,
          newState: result.new_state,
          message: result.message,
          newStart: result.new_start,
          newEnd: result.new_end,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reschedule");
      setModalState("error");
    }
  };

  const handleSkip = async () => {
    setApplyingId("skip");
    setModalState("applying");
    try {
      if (USE_MOCK) {
        await new Promise((r) => setTimeout(r, 500));
        onReschedule({
          action: "skip",
          newState: "missed",
          message:
            "Task skipped. I'll keep the next occurrence on your schedule.",
        });
      } else {
        const result = await applyReschedule({
          event_id: eventId,
          action: "skip",
        });
        onReschedule({
          action: result.action,
          newState: result.new_state,
          message: result.message,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to skip task");
      setModalState("error");
    }
  };

  const isToday = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    return date.toDateString() === now.toDateString();
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
            className="fixed inset-0 bg-charcoal/30 z-50"
            style={{ backdropFilter: "blur(8px)" }}
          />

          {/* Modal */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 z-50"
          >
            <div className="glass-card rounded-b-none p-6 pb-safe relative">
              {/* Close button */}
              <button
                type="button"
                onClick={onClose}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-charcoal/10 transition-colors"
              >
                <X className="w-5 h-5 text-charcoal" />
              </button>

              {/* ── Loading State ── */}
              {modalState === "loading" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-4"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Loader2 className="w-4 h-4 text-river animate-spin" />
                    <p className="text-river text-sm">Finding the best times...</p>
                  </div>
                  {/* Skeleton buttons */}
                  {[1, 2].map((i) => (
                    <div key={i} className="glass-bubble p-4 animate-pulse">
                      <div className="h-4 bg-charcoal/10 rounded w-3/4 mb-2" />
                      <div className="h-3 bg-charcoal/5 rounded w-1/2" />
                    </div>
                  ))}
                </motion.div>
              )}

              {/* ── Error State ── */}
              {modalState === "error" && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-4"
                >
                  <AlertCircle className="w-8 h-8 text-terracotta mx-auto mb-3" />
                  <p className="text-charcoal text-sm mb-4">
                    {error || "Something went wrong"}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setModalState("loading");
                      const reload = async () => {
                        try {
                          const result = USE_MOCK
                            ? {
                                ...MOCK_RESPONSE,
                                event_id: eventId,
                                task_title: taskTitle,
                              }
                            : await fetchSuggestions(eventId);
                          setData(result);
                          setModalState("ready");
                        } catch (err) {
                          setError(
                            err instanceof Error
                              ? err.message
                              : "Still failing",
                          );
                          setModalState("error");
                        }
                      };
                      reload();
                    }}
                    className="glass-bubble px-6 py-2 text-sm font-medium text-river"
                  >
                    Try Again
                  </button>
                </motion.div>
              )}

              {/* ── Ready State (suggestions loaded) ── */}
              {(modalState === "ready" || modalState === "applying") &&
                data && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    {/* AI Message */}
                    <div className="mb-5">
                      <p className="text-river text-sm mb-2">Shuffle</p>
                      <div
                        className={cn(
                          "glass-bubble p-4 transform -rotate-1 relative",
                          "border-l-4 border-l-terracotta",
                        )}
                      >
                        <p className="text-charcoal font-medium">
                          {data.ai_message}
                        </p>
                        {useVoice && isVoiceSupported && isListening && (
                          <div className="flex items-center gap-2 mt-2 text-river/80">
                            <span className="flex items-center gap-1.5 text-xs">
                              <span className="w-2 h-2 rounded-full bg-terracotta animate-pulse" />
                              <Mic className="w-3.5 h-3.5" />
                              Listening...
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Suggestion Buttons */}
                    <div className="space-y-3 mb-3">
                      {data.suggestions.map((suggestion, index) => {
                        const isTodaySlot = isToday(suggestion.new_start);
                        const Icon = isTodaySlot ? Clock : Sun;
                        const isApplying = applyingId === suggestion.label;

                        return (
                          <motion.button
                            key={suggestion.label}
                            type="button"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + index * 0.1 }}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            disabled={modalState === "applying"}
                            onClick={() => handleSuggestionClick(suggestion)}
                            className={cn(
                              "glass-bubble p-4 w-full text-left flex items-start gap-3",
                              "transition-all duration-200",
                              modalState === "applying" &&
                                !isApplying &&
                                "opacity-50",
                            )}
                          >
                            {isApplying ? (
                              <Loader2 className="w-5 h-5 text-sage animate-spin mt-0.5 shrink-0" />
                            ) : (
                              <Icon
                                className={cn(
                                  "w-5 h-5 mt-0.5 shrink-0",
                                  isTodaySlot ? "text-sage" : "text-terracotta",
                                )}
                              />
                            )}
                            <div>
                              <p className="text-charcoal font-medium text-sm">
                                {suggestion.label}
                              </p>
                              <p className="text-river/70 text-xs mt-1">
                                {suggestion.rationale}
                              </p>
                            </div>
                          </motion.button>
                        );
                      })}
                    </div>

                    {/* Skip Button */}
                    {data.skip_option && (
                      <motion.button
                        type="button"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        whileTap={{ scale: 0.98 }}
                        disabled={modalState === "applying"}
                        onClick={handleSkip}
                        className={cn(
                          "w-full p-3 text-center flex items-center justify-center gap-2",
                          "text-river/60 text-sm rounded-xl",
                          "hover:bg-charcoal/5 transition-colors",
                          modalState === "applying" &&
                            applyingId !== "skip" &&
                            "opacity-50",
                        )}
                      >
                        {applyingId === "skip" ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <SkipForward className="w-4 h-4" />
                        )}
                        Skip Today
                      </motion.button>
                    )}
                  </motion.div>
                )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

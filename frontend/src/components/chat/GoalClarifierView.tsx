import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useState } from "react";
import type {
  GoalClarifierAnswer,
  GoalClarifierQuestion,
} from "~/types/message";
import { cn } from "~/utils/cn";

interface GoalClarifierViewProps {
  questions: GoalClarifierQuestion[];
  onSubmit: (answers: GoalClarifierAnswer[]) => void;
  onDismiss: () => void;
  disabled?: boolean;
}

/**
 * Bottom sheet that steps through goal clarifier questions one-by-one.
 * Collects all answers locally, then calls onSubmit with the full batch.
 */
export function GoalClarifierView({
  questions,
  onSubmit,
  onDismiss,
  disabled,
}: GoalClarifierViewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<GoalClarifierAnswer[]>([]);
  const [customValue, setCustomValue] = useState("");
  const [customError, setCustomError] = useState<string | null>(null);

  if (questions.length === 0) return null;

  const current = questions[currentIndex];
  const isLast = currentIndex + 1 === questions.length;

  function recordAnswer(answer: string) {
    const newAnswer: GoalClarifierAnswer = {
      question_id: current.id,
      question: current.question,
      answer,
    };
    const updatedAnswers = [...answers, newAnswer];

    if (!isLast) {
      setAnswers(updatedAnswers);
      setCurrentIndex(currentIndex + 1);
      setCustomValue("");
      setCustomError(null);
    } else {
      onSubmit(updatedAnswers);
    }
  }

  function handleCustomSubmit() {
    const trimmed = customValue.trim();
    if (!trimmed) {
      setCustomError("Please enter a value");
      return;
    }
    recordAnswer(trimmed);
  }

  // Progress: fraction of questions answered (0 → empty, 1 → full)
  const progressFraction = currentIndex / questions.length;

  return (
    <>
      {/* Backdrop */}
      <motion.div
        className="fixed inset-0 z-40 bg-black/30"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onDismiss}
      />

      {/* Sheet */}
      <motion.div
        className="fixed bottom-0 left-0 right-0 z-50 max-w-md mx-auto rounded-t-2xl bg-white/95 backdrop-blur-xl border-t border-glass-border"
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
      >
        {/* Progress bar */}
        {questions.length > 1 && (
          <div className="h-1 rounded-t-2xl overflow-hidden bg-charcoal/10">
            <motion.div
              className="h-full bg-sage"
              initial={{ width: 0 }}
              animate={{ width: `${progressFraction * 100}%` }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
            />
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <div>
            <p className="text-xs text-river/60 font-medium uppercase tracking-wide">
              {questions.length > 1
                ? `Question ${currentIndex + 1} of ${questions.length}`
                : "Quick question"}
            </p>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-black/5 text-river hover:text-charcoal transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Question */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.18 }}
            className="px-5 pb-8 space-y-4"
          >
            <p className="text-base font-medium text-charcoal leading-snug">
              {current.question}
            </p>

            {/* Pre-defined options */}
            {current.options.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {current.options.map((opt) => (
                  <motion.button
                    key={opt}
                    type="button"
                    onClick={() => !disabled && recordAnswer(opt)}
                    disabled={disabled}
                    whileTap={{ scale: 0.96 }}
                    className={cn(
                      "px-4 py-2 rounded-full text-sm font-medium border transition-colors",
                      "bg-white border-charcoal/20 text-charcoal",
                      "hover:bg-sage/10 hover:border-sage active:bg-sage/20",
                      "disabled:opacity-40 disabled:cursor-not-allowed",
                    )}
                  >
                    {opt}
                  </motion.button>
                ))}
              </div>
            )}

            {/* Custom input */}
            {(current.allows_custom || current.options.length === 0) && (
              <div className="space-y-1">
                <div className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={customValue}
                    onChange={(e) => {
                      setCustomValue(e.target.value);
                      setCustomError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCustomSubmit();
                    }}
                    placeholder={
                      current.options.length > 0
                        ? "Or type your own…"
                        : "Type your answer…"
                    }
                    disabled={disabled}
                    className={cn(
                      "flex-1 px-3 py-2.5 text-sm rounded-xl border bg-white text-charcoal",
                      "placeholder:text-river/50 outline-none transition-colors",
                      customError
                        ? "border-red-400 focus:border-red-500"
                        : "border-charcoal/20 focus:border-sage",
                    )}
                  />
                  <button
                    type="button"
                    onClick={handleCustomSubmit}
                    disabled={disabled || !customValue.trim()}
                    className={cn(
                      "px-4 py-2.5 rounded-xl text-sm font-medium transition-colors",
                      "bg-sage text-white",
                      "hover:bg-sage/90 disabled:opacity-40 disabled:cursor-not-allowed",
                    )}
                  >
                    {isLast ? "Done" : "Next"}
                  </button>
                </div>
                {customError && (
                  <p className="text-red-500 text-xs pl-1">{customError}</p>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </motion.div>
    </>
  );
}

import { AnimatePresence, motion } from "framer-motion";
import { Calendar, CheckCircle2, Clock, X } from "lucide-react";
import { cn } from "~/utils/cn";
import type { TimelineEvent } from "~/types";

interface TaskDetailSheetProps {
  task: TimelineEvent | null;
  onClose: () => void;
  onComplete: (taskId: string) => void;
  onMissed: (taskId: string) => void;
  onReschedule: (taskId: string, taskTitle: string) => void;
}

export function TaskDetailSheet({
  task,
  onClose,
  onComplete,
  onMissed,
  onReschedule,
}: TaskDetailSheetProps) {
  if (!task) return null;

  const isMissed = task.status === "missed";
  const isDone = task.status === "done" || task.status === "completed";

  const statusLabel = isMissed
    ? "Missed"
    : isDone
      ? "Completed"
      : "Upcoming";

  const statusColor = isMissed
    ? "text-red-400"
    : isDone
      ? "text-green-400"
      : "text-river";

  return (
    <AnimatePresence>
      {task && (
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

          {/* Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="fixed bottom-0 left-0 right-0 z-50 max-w-md mx-auto"
          >
            <div className="glass-card rounded-b-none p-6 pb-safe space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex-1 pr-4">
                  <p className={cn("text-xs font-semibold uppercase tracking-widest mb-1", statusColor)}>
                    {statusLabel}
                  </p>
                  <h2 className="text-xl font-bold text-charcoal leading-snug">
                    {task.title}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="p-2 rounded-full hover:bg-charcoal/10 transition-colors shrink-0"
                >
                  <X className="w-5 h-5 text-charcoal" />
                </button>
              </div>

              {/* Meta */}
              <div className="flex items-center gap-4 text-sm text-river">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  {task.time} {task.period}
                </span>
                {task.durationMinutes && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4" />
                    {task.durationMinutes} min
                  </span>
                )}
              </div>

              {/* Description */}
              {task.description && (
                <p className="text-sm text-charcoal/70 leading-relaxed">
                  {task.description}
                </p>
              )}

              {/* CTAs */}
              <div className="flex flex-col gap-3 pt-1">
                {/* Acknowledged — always shown for pending tasks */}
                {!isDone && !isMissed && (
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.97 }}
                    onClick={() => { onComplete(task.id); onClose(); }}
                    className="w-full glass-bubble flex items-center justify-center gap-2 py-3.5 rounded-2xl text-charcoal font-medium"
                  >
                    <CheckCircle2 className="w-5 h-5 text-river" />
                    Acknowledged
                  </motion.button>
                )}

                {/* Mark as Done — shown for missed tasks */}
                {isMissed && (
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.97 }}
                    onClick={() => { onComplete(task.id); onClose(); }}
                    className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-medium text-white bg-green-500/80"
                  >
                    <CheckCircle2 className="w-5 h-5" />
                    Mark as Done
                  </motion.button>
                )}

                {/* Reschedule — shown for pending and missed tasks */}
                {!isDone && (
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.97 }}
                    onClick={() => { onReschedule(task.id, task.title); onClose(); }}
                    className="w-full glass-bubble flex items-center justify-center gap-2 py-3.5 rounded-2xl text-terracotta font-medium"
                  >
                    <Calendar className="w-5 h-5" />
                    Reschedule
                  </motion.button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

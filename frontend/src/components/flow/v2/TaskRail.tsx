import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { TaskRailItem } from "~/types";
import { cn } from "~/utils/cn";

const MAX_TITLE_LENGTH = 500;
const RAIL_MAX_INCOMPLETE = 10;
const ALL_TASKS_PAGE_SIZE = 20;

interface TaskRailProps {
  tasks: TaskRailItem[];
  onComplete?: (taskId: string) => void;
  onAddTodo?: (title: string) => void;
}

// ─── Add Task Modal ───────────────────────────────────────────────────────────

interface AddTaskModalProps {
  onClose: () => void;
  onSubmit: (title: string) => void;
}

function AddTaskModal({ onClose, onSubmit }: AddTaskModalProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setValue(v);
    if (v.trim().length === 0) {
      setError("");
    } else if (v.length > MAX_TITLE_LENGTH) {
      setError(`Title must be ${MAX_TITLE_LENGTH} characters or fewer.`);
    } else {
      setError("");
    }
  };

  const handleSubmit = () => {
    const title = value.trim();
    if (!title) {
      setError("Task title is required.");
      return;
    }
    if (title.length > MAX_TITLE_LENGTH) {
      setError(`Title must be ${MAX_TITLE_LENGTH} characters or fewer.`);
      return;
    }
    onSubmit(title);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSubmit();
    if (e.key === "Escape") onClose();
  };

  const remaining = MAX_TITLE_LENGTH - value.length;
  const isOverLimit = value.length > MAX_TITLE_LENGTH;

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-charcoal/30 z-[70]"
        style={{ backdropFilter: "blur(8px)" }}
      />

      {/* Sheet */}
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed bottom-0 left-0 right-0 z-[70]"
      >
        <div className="glass-card rounded-b-none p-6 pb-safe">
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <p className="text-river text-sm font-semibold uppercase tracking-widest">
              New Task
            </p>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-full hover:bg-charcoal/10 transition-colors"
            >
              <X className="w-5 h-5 text-charcoal" />
            </button>
          </div>

          {/* Input */}
          <div
            className={cn(
              "glass-bubble p-4 border-2 transition-colors",
              error
                ? "border-terracotta/60"
                : "border-transparent focus-within:border-sage/40",
            )}
          >
            <input
              ref={inputRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="What needs to get done?"
              maxLength={MAX_TITLE_LENGTH + 1}
              className="w-full bg-transparent text-sm font-medium text-charcoal placeholder-river/40 outline-none leading-relaxed"
            />
          </div>

          {/* Footer row: char count + error + submit */}
          <div className="flex items-start justify-between mt-3">
            <div className="flex-1 pr-4">
              {error && (
                <p className="text-xs text-terracotta font-medium">{error}</p>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span
                className={cn(
                  "text-xs font-medium",
                  isOverLimit ? "text-terracotta" : "text-river/50",
                )}
              >
                {remaining}
              </span>
              <motion.button
                type="button"
                onClick={handleSubmit}
                disabled={isOverLimit || value.trim().length === 0}
                whileTap={{ scale: 0.95 }}
                className={cn(
                  "px-5 py-2 rounded-full text-sm font-semibold transition-colors",
                  isOverLimit || value.trim().length === 0
                    ? "bg-river/20 text-river/40 cursor-not-allowed"
                    : "bg-sage text-white hover:bg-sage/90",
                )}
              >
                Add Task
              </motion.button>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

// ─── All Tasks Modal ──────────────────────────────────────────────────────────

interface AllTasksModalProps {
  tasks: TaskRailItem[];
  onClose: () => void;
  onComplete?: (taskId: string) => void;
}

function AllTasksModal({ tasks, onClose, onComplete }: AllTasksModalProps) {
  const [visibleCount, setVisibleCount] = useState(ALL_TASKS_PAGE_SIZE);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const incomplete = tasks.filter((t) => !t.completed);
  const completed = tasks.filter((t) => t.completed);
  const ordered = [...incomplete, ...completed];
  const visible = ordered.slice(0, visibleCount);
  const hasMore = visibleCount < ordered.length;

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore) {
          setVisibleCount((n) => n + ALL_TASKS_PAGE_SIZE);
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore]);

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-charcoal/30 z-[70]"
        style={{ backdropFilter: "blur(8px)" }}
      />

      {/* Sheet */}
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed bottom-0 left-0 right-0 z-[70] max-h-[75vh] flex flex-col"
      >
        <div className="glass-card rounded-b-none flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4 shrink-0">
            <div>
              <p className="text-river text-sm font-semibold uppercase tracking-widest">
                All Tasks
              </p>
              <p className="text-xs text-river/50 mt-0.5">
                {incomplete.length} pending · {completed.length} done
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-full hover:bg-charcoal/10 transition-colors"
            >
              <X className="w-5 h-5 text-charcoal" />
            </button>
          </div>

          {/* List */}
          <div className="overflow-y-auto flex-1 px-6 pb-safe">
            {ordered.length === 0 ? (
              <p className="text-sm text-river/50 text-center py-8">
                No tasks yet.
              </p>
            ) : (
              <div className="space-y-2 pb-6">
                {visible.map((task) => (
                  <motion.div
                    key={task.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      "flex items-center gap-3 glass-bubble px-4 py-3 rounded-2xl",
                      task.completed && "opacity-60",
                    )}
                  >
                    <button
                      type="button"
                      aria-label={task.completed ? "Completed" : "Mark as done"}
                      onClick={() => !task.completed && onComplete?.(task.id)}
                      className="shrink-0"
                    >
                      <div
                        className={cn(
                          "w-5 h-5 rounded-full border-2 transition-colors",
                          task.completed
                            ? "bg-sage border-sage"
                            : "border-river hover:border-sage",
                        )}
                      />
                    </button>
                    <span
                      className={cn(
                        "text-sm font-medium text-charcoal leading-tight flex-1",
                        task.completed && "line-through",
                      )}
                    >
                      {task.title}
                    </span>
                  </motion.div>
                ))}
                {/* Infinite scroll sentinel */}
                <div ref={sentinelRef} className="h-4" />
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

// ─── TaskRail ─────────────────────────────────────────────────────────────────

export function TaskRail({ tasks, onComplete, onAddTodo }: TaskRailProps) {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [allTasksOpen, setAllTasksOpen] = useState(false);

  const incomplete = tasks.filter((t) => !t.completed);
  const railTasks = incomplete.slice(0, RAIL_MAX_INCOMPLETE);
  const uncompletedCount = incomplete.length;

  const handleAddSubmit = (title: string) => {
    onAddTodo?.(title);
  };

  return (
    <>
      <div className="px-6 mb-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-xs font-bold text-river uppercase tracking-widest">
            Tasks
          </h2>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-sage font-semibold bg-sage/10 px-2 py-0.5 rounded-full">
              {uncompletedCount} left
            </span>
            <button
              type="button"
              onClick={() => setAllTasksOpen(true)}
              className="text-xs text-river/70 font-medium hover:text-river transition-colors px-2 py-0.5 rounded-full hover:bg-river/10"
            >
              All Tasks
            </button>
            <button
              type="button"
              onClick={() => setAddModalOpen(true)}
              className="text-xs text-sage font-semibold hover:text-sage/80 transition-colors px-2 py-0.5 rounded-full hover:bg-sage/10"
            >
              + Add
            </button>
          </div>
        </div>

        {/* Rail */}
        <div className="flex overflow-x-auto scrollbar-hide pb-2 snap-x space-x-2 pt-1">
          {railTasks.map((task) => (
            <div key={task.id} className="snap-start shrink-0">
              <div className="glass-pebble-stone py-3 px-4 rounded-2xl w-[11rem] flex flex-col justify-center relative h-20 hover:shadow-lg transition-shadow cursor-pointer group mt-2 mr-1.5">
                <div className="absolute -top-3 -right-3 z-10">
                  <button
                    type="button"
                    aria-label="Mark as done"
                    onClick={() => onComplete?.(task.id)}
                    className="w-8 h-8 bg-stone border border-white/50 shadow-sm rounded-full flex items-center justify-center group-hover:border-sage transition-colors"
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-river group-hover:border-sage transition-colors" />
                  </button>
                </div>
                <span className="text-sm font-medium text-charcoal leading-tight text-ellipsis-2-lines">
                  {task.title}
                </span>
              </div>
            </div>
          ))}

          {railTasks.length === 0 && (
            <div className="flex items-center justify-center w-full h-20 mt-2">
              <p className="text-xs text-river/40 font-medium">
                No pending tasks
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {addModalOpen && (
          <AddTaskModal
            onClose={() => setAddModalOpen(false)}
            onSubmit={handleAddSubmit}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {allTasksOpen && (
          <AllTasksModal
            tasks={tasks}
            onClose={() => setAllTasksOpen(false)}
            onComplete={onComplete}
          />
        )}
      </AnimatePresence>
    </>
  );
}

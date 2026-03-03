import { Link } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { AnalyticsGoalItem } from "~/utils/api";
import { cn } from "~/utils/cn";

interface GoalCardProps {
  goal: AnalyticsGoalItem;
}

export function GoalCard({ goal }: GoalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(goal.completion_pct * 100);

  return (
    <motion.div
      className="glass-card rounded-2xl overflow-hidden shadow-ambient"
      layout
    >
      <button
        type="button"
        className="w-full text-left p-4 flex items-center justify-between gap-2"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="min-w-0 flex-1">
          <h4 className="font-medium text-charcoal truncate">{goal.title}</h4>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="flex-1 h-2 rounded-full bg-river/20 overflow-hidden max-w-[180px]">
              <div
                className="h-full rounded-full bg-sage transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-river/80 shrink-0">{pct}%</span>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-river shrink-0" />
        ) : (
          <ChevronDown className="w-5 h-5 text-river shrink-0" />
        )}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-glass-border overflow-hidden"
          >
            <div className="p-4 pt-2 space-y-2">
              <p className="text-sm text-river/80">
                {goal.tasks_done} of {goal.tasks_total} tasks completed
              </p>
              <Link
                to="/"
                className={cn(
                  "inline-flex items-center text-sm font-medium text-sage",
                  "hover:underline",
                )}
              >
                View Tasks
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

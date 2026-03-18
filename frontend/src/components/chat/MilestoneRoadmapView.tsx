import { motion } from "framer-motion";
import { Flag, Lock, Milestone } from "lucide-react";
import { cn } from "~/utils/cn";

export interface RoadmapMilestone {
  title: string;
  description: string;
  pipeline_order: number;
  target_weeks: number;
}

interface MilestoneRoadmapViewProps {
  milestones: RoadmapMilestone[];
}

export function MilestoneRoadmapView({
  milestones,
}: MilestoneRoadmapViewProps) {
  const sorted = [...milestones].sort(
    (a, b) => a.pipeline_order - b.pipeline_order,
  );

  return (
    <div className="space-y-4 my-4">
      <div className="flex items-center gap-2 mb-1">
        <Milestone className="w-5 h-5 text-sage" />
        <h3 className="text-river font-semibold">Your Milestone Roadmap</h3>
      </div>

      <p className="text-sm text-river/70 leading-relaxed">
        Your goal is ambitious — we've broken it into milestones so each step
        feels achievable and sustainable. We'll start with the first milestone,
        and when you're ready, Flux will guide you through the next one.
      </p>

      <div className="space-y-3">
        {sorted.map((ms, index) => {
          const isFirst = index === 0;
          return (
            <motion.div
              key={ms.pipeline_order}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.08 }}
              className={cn(
                "relative pl-5 pb-1 border-l-2 last:border-0",
                isFirst ? "border-sage" : "border-sage/25",
              )}
            >
              {/* Timeline dot */}
              <span
                className={cn(
                  "absolute left-[-9px] top-1 w-4 h-4 rounded-full flex items-center justify-center",
                  isFirst ? "bg-sage" : "bg-sand border-2 border-sage/30",
                )}
              >
                {isFirst ? (
                  <Flag className="w-2.5 h-2.5 text-white" />
                ) : (
                  <Lock className="w-2.5 h-2.5 text-river/40" />
                )}
              </span>

              <div
                className={cn(
                  "rounded-xl p-3.5 border shadow-sm",
                  isFirst
                    ? "bg-white/70 backdrop-blur-sm border-sage/20"
                    : "bg-white/30 backdrop-blur-sm border-sage/10 opacity-70",
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span
                    className={cn(
                      "text-xs font-bold uppercase tracking-wider",
                      isFirst ? "text-sage" : "text-river/50",
                    )}
                  >
                    {isFirst
                      ? "Starting here"
                      : `Milestone ${ms.pipeline_order}`}
                  </span>
                  <span className="text-xs text-river/50">
                    {ms.target_weeks} weeks
                  </span>
                </div>
                <p
                  className={cn(
                    "text-sm font-semibold",
                    isFirst ? "text-charcoal" : "text-river/60",
                  )}
                >
                  {ms.title}
                </p>
                {ms.description && (
                  <p
                    className={cn(
                      "text-xs mt-0.5 leading-relaxed",
                      isFirst ? "text-river/70" : "text-river/40",
                    )}
                  >
                    {ms.description}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

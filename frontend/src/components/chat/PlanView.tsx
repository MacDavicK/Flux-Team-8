import { motion } from "framer-motion";
import { CheckCircle2, Info, Trophy } from "lucide-react";
import type { PlanMilestone } from "~/types/goal";
import type { RAGSource } from "~/utils/api";
import { cn } from "~/utils/cn";

function isUrlLike(s: string): boolean {
  return /^https?:\/\//i.test(s);
}

interface PlanViewProps {
  plan: PlanMilestone[];
  onConfirm?: () => void;
  sources?: RAGSource[];
  fallbackBannerText?: string;
}

export function PlanView({
  plan,
  onConfirm,
  sources,
  fallbackBannerText,
}: PlanViewProps) {
  const hasSources = Array.isArray(sources) && sources.length > 0;

  return (
    <div className="space-y-6 my-4">
      <div className="flex items-center gap-2 mb-2">
        <Trophy className="w-5 h-5 text-sage" />
        <h3 className="text-river font-semibold">Your Goal Roadmap</h3>
      </div>

      {fallbackBannerText ? (
        <div
          className={cn(
            "flex gap-2 p-3 rounded-lg text-sm",
            "bg-sky-100/80 dark:bg-sky-900/20 text-charcoal/90",
          )}
        >
          <Info className="w-4 h-4 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
          <p>{fallbackBannerText}</p>
        </div>
      ) : null}

      <div className="space-y-4">
        {plan.map((milestone, index) => (
          <motion.div
            key={milestone.week}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={cn(
              "relative pl-6 pb-4 border-l-2 border-sage/30 last:border-0",
              "before:content-[''] before:absolute before:left-[-9px] before:top-0 before:w-4 before:h-4 before:rounded-full before:bg-sage",
            )}
          >
            <div className="bg-white/50 backdrop-blur-sm rounded-xl p-4 border border-sage/10 shadow-sm">
              <div className="flex justify-between items-start mb-2 gap-2">
                <span className="text-xs font-bold text-sage uppercase tracking-wider">
                  {milestone.week}
                </span>
                <span className="text-xs text-river/60 font-medium">
                  {milestone.milestone}
                </span>
              </div>
              <ul className="space-y-2">
                {milestone.tasks.map((task) => (
                  <li
                    key={task}
                    className="flex items-center gap-2 text-sm text-charcoal"
                  >
                    <CheckCircle2 className="w-4 h-4 text-sage/60" />
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        ))}
      </div>

      {hasSources ? (
        <div className="pt-4 border-t border-glass-border">
          <p className="text-xs font-medium text-river/70 mb-2">
            📚 Based on expert advice:
          </p>
          <ul className="space-y-1.5 text-xs text-river/80">
            {(sources ?? []).map((s) => {
              const href =
                s.url ??
                (s.source && isUrlLike(s.source) ? s.source : undefined);
              const label =
                s.source && !isUrlLike(s.source) ? s.source : undefined;
              return (
                <li key={`${s.title}-${s.source ?? s.url ?? ""}`}>
                  &quot;{s.title}&quot;
                  {label ? ` — ${label}` : null}
                  {href ? (
                    <>
                      {" "}
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sage hover:underline"
                      >
                        [link]
                      </a>
                    </>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onConfirm}
        className="w-full py-3 bg-sage text-white rounded-2xl font-semibold shadow-lg shadow-sage/20 transition-all hover:bg-sage-dark"
      >
        Activate This Plan
      </motion.button>
    </div>
  );
}

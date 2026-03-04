import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { type AnalyticsOverviewResponse, api } from "~/utils/api";

export function StreakCard() {
  const [data, setData] = useState<AnalyticsOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api
      .analyticsOverview()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <motion.div
        className="glass-card p-6 flex flex-col items-center gap-2 rounded-2xl"
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="w-10 h-10 rounded-full bg-sage/30" />
        <div className="h-6 w-28 rounded bg-sage/30" />
        <div className="h-4 w-40 rounded bg-sage/20" />
      </motion.div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">Couldn&apos;t load streak data.</p>
      </div>
    );
  }

  const streak = data?.streak_days ?? 0;
  const todayDone = data?.today_done ?? 0;
  const todayTotal = data?.today_total ?? 0;
  const isEmpty =
    streak === 0 &&
    todayTotal === 0 &&
    (!data?.heatmap || data.heatmap.length === 0);

  return (
    <motion.div
      className="space-y-3"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="glass-card p-6 flex flex-col items-center gap-1 shadow-ambient rounded-2xl">
        <span className="text-4xl" aria-hidden>
          🔥
        </span>
        <p className="text-2xl font-bold text-charcoal">{streak} day streak</p>
        <p className="text-sm text-river/80">
          {todayDone} of {todayTotal} tasks completed today
        </p>
      </div>
      {isEmpty && (
        <p className="text-center text-sm text-river/80">
          Complete your first task to see your stats!
        </p>
      )}
    </motion.div>
  );
}

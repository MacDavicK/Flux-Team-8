import {
  createFileRoute,
  useNavigate,
  useSearch,
} from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { ActivityHeatmap } from "~/components/analytics/ActivityHeatmap";
import { GoalCard } from "~/components/analytics/GoalCard";
import { MissedByCategoryChart } from "~/components/analytics/MissedByCategoryChart";
import { StreakCard } from "~/components/analytics/StreakCard";
import { WeeklyChart } from "~/components/analytics/WeeklyChart";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { type AnalyticsGoalItem, api } from "~/utils/api";
import { cn } from "~/utils/cn";

type TabId = "overview" | "goals" | "patterns";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "goals", label: "Goals" },
  { id: "patterns", label: "Patterns" },
];

export const Route = createFileRoute("/analytics")({
  component: AnalyticsPage,
  validateSearch: (search: Record<string, unknown>) => ({
    tab: (search.tab as TabId) || "overview",
  }),
});

function AnalyticsPage() {
  const navigate = useNavigate();
  const search = useSearch({ from: "/analytics" });
  const tab = search?.tab ?? "overview";
  const activeTab = TABS.some((t) => t.id === tab) ? tab : "overview";

  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground variant="dark" />
      <header className="px-5 pt-12 pb-4 relative z-10">
        <h1 className="font-display italic text-xl text-charcoal/80">
          Progress
        </h1>
        <nav className="flex gap-1 mt-4" aria-label="Analytics tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() =>
                navigate({ to: "/analytics", search: { tab: t.id } })
              }
              className={cn(
                "px-4 py-2 rounded-full text-sm font-medium transition-colors",
                activeTab === t.id
                  ? "bg-sage text-white"
                  : "text-river hover:bg-white/10",
              )}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="px-5 space-y-6 relative z-10">
        {activeTab === "overview" && <OverviewTab />}
        {activeTab === "goals" && <GoalsTab />}
        {activeTab === "patterns" && <PatternsTab />}
      </main>

      <BottomNav />
    </div>
  );
}

function OverviewTab() {
  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <StreakCard />
      <WeeklyChart />
      <ActivityHeatmap />
      <MissedByCategoryChart />
    </motion.div>
  );
}

function GoalsTab() {
  const [goals, setGoals] = useState<AnalyticsGoalItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api
      .analyticsGoals()
      .then(setGoals)
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <motion.div
        className="space-y-3"
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass-card p-4 rounded-2xl space-y-2">
            <div className="h-5 w-3/4 rounded bg-sage/30" />
            <div className="h-2 w-full rounded bg-sage/20" />
          </div>
        ))}
      </motion.div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">Couldn&apos;t load goals.</p>
      </div>
    );
  }

  if (!goals || goals.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-river/80">Set a goal to track your progress here.</p>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-3"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {goals.map((goal) => (
        <GoalCard key={goal.goal_id} goal={goal} />
      ))}
    </motion.div>
  );
}

function PatternsTab() {
  return (
    <motion.div
      className="glass-card p-8 text-center rounded-2xl"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <p className="text-river/80">Coming soon</p>
    </motion.div>
  );
}

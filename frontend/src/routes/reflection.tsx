import { createFileRoute, redirect } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Flame } from "lucide-react";
import { GoalProgressCard } from "~/components/flow/v2/GoalProgressCard";
import { BottomNav } from "~/components/navigation/BottomNav";
import { EnergyAura } from "~/components/reflection/EnergyAura";
import {
  CATEGORY_COLORS,
  DEFAULT_COLOR,
  FocusDistribution,
} from "~/components/reflection/FocusDistribution";
import { ProfileHeader } from "~/components/reflection/ProfileHeader";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { StatPill } from "~/components/ui/StatPill";
import { serverGetMe } from "~/lib/authServerFns";
import { debugSsrLog } from "~/utils/env";

function ReflectionPagePending() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <AmbientBackground />
      <LoadingState />
    </div>
  );
}

const iconMap = {
  check: CheckCircle2,
  clock: Clock,
  flame: Flame,
} as const;

export const Route = createFileRoute("/reflection")({
  pendingComponent: ReflectionPagePending,
  pendingMs: 0,
  loader: async () => {
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    const headers = { Authorization: `Bearer ${token}` };

    const [overview, weekly, missed, goalsProgress] = await Promise.all([
      fetch(`${backendUrl}/api/v1/analytics/overview`, { headers }).then((r) =>
        r.ok ? r.json() : {},
      ),
      fetch(`${backendUrl}/api/v1/analytics/weekly`, { headers }).then((r) =>
        r.ok ? r.json() : [],
      ),
      fetch(`${backendUrl}/api/v1/analytics/missed-by-cat`, { headers }).then(
        (r) => (r.ok ? r.json() : []),
      ),
      fetch(`${backendUrl}/api/v1/goals/progress`, { headers }).then((r) =>
        r.ok ? r.json() : [],
      ),
    ]);

    const o = overview as {
      tasks_completed?: number;
      focus_hours?: number;
      streak_days?: number;
      week_label?: string;
      insight?: string;
    };

    const energyData = (weekly as { week?: string; completed?: number }[]).map(
      (w, i) => ({
        date: new Date(
          Date.now() - (6 - i) * 24 * 60 * 60 * 1000,
        ).toISOString(),
        intensity: Math.min(1, (w.completed ?? 0) / 6),
      }),
    );

    const byCategory = missed as { category?: string; missed_count?: number }[];
    const totalMissed =
      byCategory.reduce((s, c) => s + (c.missed_count ?? 0), 0) || 1;
    const focusCategories = byCategory
      .filter((c) => c.category)
      .map((c) => ({
        name: c.category ?? "",
        count: c.missed_count ?? 0,
        percent: Math.round(((c.missed_count ?? 0) / totalMissed) * 100),
        color: CATEGORY_COLORS[c.category ?? ""] ?? DEFAULT_COLOR,
      }));

    const data = {
      profile: user
        ? { id: user.id, name: user.name ?? "User", email: user.email }
        : null,
      goalsProgress: Array.isArray(goalsProgress) ? goalsProgress : [],
      stats: {
        title: o.week_label ?? "This Week",
        items: [
          {
            icon: "check" as const,
            value: String(o.tasks_completed ?? 0),
            label: "Done",
          },
          {
            icon: "clock" as const,
            value: `${o.focus_hours ?? 0}h`,
            label: "Focus",
          },
          {
            icon: "flame" as const,
            value: String(o.streak_days ?? 0),
            label: "Streak",
          },
        ],
      },
      insight: {
        title: "This Week's Insight",
        text:
          o.insight ?? "Keep up the great work! You're building strong habits.",
      },
      energyData,
      focusCategories,
    };
    debugSsrLog("/reflection (ReflectionPage)", data);
    return data;
  },
  component: ReflectionPage,
});

function ReflectionPage() {
  const {
    profile,
    stats,
    insight,
    energyData,
    focusCategories,
    goalsProgress,
  } = Route.useLoaderData();

  if (!profile) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground />

      <ProfileHeader
        name={profile.name}
        avatarUrl={undefined}
        settingsTo="/profile"
      />

      <GoalProgressCard initialGoals={goalsProgress} />

      <main className="px-5 space-y-6">
        <h2 className="text-display text-2xl italic text-charcoal">
          Your reflection
        </h2>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
            {stats.title}
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {stats.items.map((stat) => {
              const IconComponent = iconMap[stat.icon];
              return (
                <StatPill
                  key={stat.label}
                  icon={<IconComponent className="w-5 h-5" />}
                  value={stat.value}
                  label={stat.label}
                />
              );
            })}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <EnergyAura data={energyData} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <FocusDistribution categories={focusCategories} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="glass-card p-5">
            <h3 className="text-display italic text-lg text-charcoal mb-2">
              {insight.title}
            </h3>
            <p className="text-river text-sm leading-relaxed">{insight.text}</p>
          </div>
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}

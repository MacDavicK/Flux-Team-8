import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Flame, SlidersHorizontal } from "lucide-react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { EnergyAura } from "~/components/reflection/EnergyAura";
import { FocusDistribution } from "~/components/reflection/FocusDistribution";
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

    const [overview, weekly, missed] = await Promise.all([
      fetch(`${backendUrl}/api/v1/analytics/overview`, { headers }).then((r) => r.ok ? r.json() : {}),
      fetch(`${backendUrl}/api/v1/analytics/weekly`, { headers }).then((r) => r.ok ? r.json() : []),
      fetch(`${backendUrl}/api/v1/analytics/missed-by-cat`, { headers }).then((r) => r.ok ? r.json() : []),
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
        date: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString(),
        intensity: Math.min(1, (w.completed ?? 0) / 6),
      }),
    );

    const byCategory = missed as { category?: string; count?: number }[];
    const work = byCategory.find((c) => c.category === "work")?.count ?? 0;
    const personal = byCategory.find((c) => c.category === "personal")?.count ?? 0;
    const health = byCategory.find((c) => c.category === "health")?.count ?? 0;
    const total = work + personal + health || 1;

    const data = {
      profile: user ? { id: user.id, name: user.name ?? "User", email: user.email } : null,
      stats: {
        title: o.week_label ?? "This Week",
        items: [
          { icon: "check" as const, value: String(o.tasks_completed ?? 0), label: "Done" },
          { icon: "clock" as const, value: `${o.focus_hours ?? 0}h`, label: "Focus" },
          { icon: "flame" as const, value: String(o.streak_days ?? 0), label: "Streak" },
        ],
      },
      insight: {
        title: "This Week's Insight",
        text: o.insight ?? "Keep up the great work! You're building strong habits.",
      },
      energyData,
      focusData: {
        work: Math.round((work / total) * 100),
        personal: Math.round((personal / total) * 100),
        health: Math.round((health / total) * 100),
      },
    };
    debugSsrLog("/reflection (ReflectionPage)", data);
    return data;
  },
  component: ReflectionPage,
});

function ReflectionPage() {
  const { profile, stats, insight, energyData, focusData } = Route.useLoaderData();

  if (!profile) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground />

      <ProfileHeader name={profile.name} avatarUrl={undefined} />

      <main className="px-5 space-y-6">
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
          <FocusDistribution
            work={focusData.work}
            personal={focusData.personal}
            health={focusData.health}
          />
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
            <p className="text-river text-sm leading-relaxed">
              {insight.text}
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="pb-2"
        >
          <Link
            to="/profile"
            className="w-full glass-card p-4 flex items-center gap-3 hover:bg-white/30 transition-colors duration-200 active:scale-[0.98]"
          >
            <div className="w-10 h-10 rounded-2xl fab-gradient flex items-center justify-center shrink-0">
              <SlidersHorizontal className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-charcoal">Tune your preferences</p>
              <p className="text-xs text-river/60 mt-0.5">Schedule, timezone & notifications</p>
            </div>
          </Link>
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Flame } from "lucide-react";
import { useEffect, useState } from "react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { EnergyAura } from "~/components/reflection/EnergyAura";
import { EnergyAuraLoadingState } from "~/components/reflection/EnergyAuraLoadingState";
import { FocusDistribution } from "~/components/reflection/FocusDistribution";
import { FocusDistributionLoadingState } from "~/components/reflection/FocusDistributionLoadingState";
import { ProfileHeader } from "~/components/reflection/ProfileHeader";
import { StatsLoadingState } from "~/components/reflection/StatsLoadingState";
import { WeeklyInsightLoadingState } from "~/components/reflection/WeeklyInsightLoadingState";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { StatPill } from "~/components/ui/StatPill";
import { accountService } from "~/services/AccountService";

type StatsResponse = {
  title: string;
  stats: { icon: "check" | "clock" | "flame"; value: string; label: string }[];
};
type EnergyAuraResponse = { data: { date: string; intensity: number }[] };
type FocusDistributionResponse = {
  work: number;
  personal: number;
  health: number;
};
type WeeklyInsightResponse = { title: string; insight: string };

const iconMap = {
  check: CheckCircle2,
  clock: Clock,
  flame: Flame,
};

export const Route = createFileRoute("/reflection")({
  component: ReflectionPage,
  loader: async () => {
    const me = await accountService.getMe();
    return {
      profile: { id: me.id, name: me.email ?? "User", email: me.email ?? "" },
    };
  },
});

function ReflectionPage() {
  const { profile } = Route.useLoaderData();

  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [energyData, setEnergyData] = useState<EnergyAuraResponse | null>(null);
  const [focusData, setFocusData] = useState<FocusDistributionResponse | null>(
    null,
  );
  const [insight, setInsight] = useState<WeeklyInsightResponse | null>(null);

  useEffect(() => {
    accountService.getOverview().then((overview) => {
      const o = overview as {
        tasks_completed?: number;
        focus_hours?: number;
        streak_days?: number;
        week_label?: string;
        insight?: string;
      };
      setStats({
        title: o.week_label ?? "This Week",
        stats: [
          {
            icon: "check",
            value: String(o.tasks_completed ?? 0),
            label: "Done",
          },
          { icon: "clock", value: `${o.focus_hours ?? 0}h`, label: "Focus" },
          { icon: "flame", value: String(o.streak_days ?? 0), label: "Streak" },
        ],
      });
      setInsight({
        title: "This Week's Insight",
        insight:
          o.insight ?? "Keep up the great work! You're building strong habits.",
      });
    });

    accountService.getWeeklyStats().then((weekly) => {
      const data = (weekly as { week?: string; completed?: number }[]).map(
        (w, i) => ({
          date: new Date(
            Date.now() - (6 - i) * 24 * 60 * 60 * 1000,
          ).toISOString(),
          intensity: Math.min(1, (w.completed ?? 0) / 6),
        }),
      );
      setEnergyData({ data });
    });

    accountService.getMissedByCategory().then((missed) => {
      const byCategory = missed as { category?: string; count?: number }[];
      const work = byCategory.find((c) => c.category === "work")?.count ?? 0;
      const personal =
        byCategory.find((c) => c.category === "personal")?.count ?? 0;
      const health =
        byCategory.find((c) => c.category === "health")?.count ?? 0;
      const total = work + personal + health || 1;
      setFocusData({
        work: Math.round((work / total) * 100),
        personal: Math.round((personal / total) * 100),
        health: Math.round((health / total) * 100),
      });
    });
  }, []);

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
          {stats ? (
            <>
              <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
                {stats.title}
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {stats.stats.map((stat) => {
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
            </>
          ) : (
            <StatsLoadingState />
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {energyData ? (
            <EnergyAura data={energyData.data} />
          ) : (
            <EnergyAuraLoadingState />
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          {focusData ? (
            <FocusDistribution
              work={focusData.work}
              personal={focusData.personal}
              health={focusData.health}
            />
          ) : (
            <FocusDistributionLoadingState />
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          {insight ? (
            <div className="glass-card p-5">
              <h3 className="text-display italic text-lg text-charcoal mb-2">
                {insight.title}
              </h3>
              <p className="text-river text-sm leading-relaxed">
                {insight.insight}
              </p>
            </div>
          ) : (
            <WeeklyInsightLoadingState />
          )}
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}

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
import { userService } from "~/services/UserService";
import type {
  UserEnergyAuraResponse,
  UserFocusDistributionResponse,
  UserStatsResponse,
  UserWeeklyInsightResponse,
} from "~/types";

const iconMap = {
  check: CheckCircle2,
  clock: Clock,
  flame: Flame,
};

export const Route = createFileRoute("/reflection")({
  component: ReflectionPage,
  loader: async () => {
    const profile = await userService.getProfile();
    return { profile };
  },
});

function ReflectionPage() {
  const { profile } = Route.useLoaderData();

  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [energyData, setEnergyData] = useState<UserEnergyAuraResponse | null>(
    null,
  );
  const [focusData, setFocusData] =
    useState<UserFocusDistributionResponse | null>(null);
  const [insight, setInsight] = useState<UserWeeklyInsightResponse | null>(
    null,
  );

  useEffect(() => {
    userService.getStats().then(setStats);
    userService.getEnergyAura().then(setEnergyData);
    userService.getFocusDistribution().then(setFocusData);
    userService.getWeeklyInsight().then(setInsight);
  }, []);

  if (!profile) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground />

      <ProfileHeader name={profile.name} avatarUrl={profile.avatar} />

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

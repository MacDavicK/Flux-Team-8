import { createFileRoute } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { CheckCircle2, Clock, Flame } from "lucide-react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { EnergyAura } from "~/components/reflection/EnergyAura";
import { FocusDistribution } from "~/components/reflection/FocusDistribution";
import { ProfileHeader } from "~/components/reflection/ProfileHeader";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { StatPill } from "~/components/ui/StatPill";

const energyData = Array.from({ length: 50 }, (_, i) => ({
  date: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
  intensity: Math.random(),
}));

export const Route = createFileRoute("/reflection")({
  component: ReflectionPage,
});

function ReflectionPage() {
  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground />

      <ProfileHeader name="Harshal" />

      <main className="px-5 space-y-6">
        <motion.div
          className="grid grid-cols-3 gap-3"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <StatPill
            icon={<CheckCircle2 className="w-5 h-5" />}
            value="24"
            label="Done"
          />
          <StatPill
            icon={<Clock className="w-5 h-5" />}
            value="12h"
            label="Focus"
          />
          <StatPill
            icon={<Flame className="w-5 h-5" />}
            value="7"
            label="Streak"
          />
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
          <FocusDistribution work={45} personal={30} health={25} />
        </motion.div>

        <motion.div
          className="glass-card p-5"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <h3 className="text-display italic text-lg text-charcoal mb-2">
            This Week's Insight
          </h3>
          <p className="text-river text-sm leading-relaxed">
            Your peak productivity happens on Tuesday mornings. Consider
            scheduling your most important tasks during this time window for
            optimal focus and energy.
          </p>
        </motion.div>
      </main>

      <BottomNav />
    </div>
  );
}

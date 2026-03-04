import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { type AnalyticsWeeklyItem, api } from "~/utils/api";
import { WidgetSkeleton } from "./WidgetSkeleton";

function formatWeekLabel(weekStart: string): string {
  try {
    const d = new Date(weekStart);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return weekStart;
  }
}

export function WeeklyChart() {
  const [data, setData] = useState<AnalyticsWeeklyItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api
      .analyticsWeekly(12)
      .then((raw) => {
        const reversed = [...raw].reverse();
        setData(
          reversed.map((item) => ({
            ...item,
            pct: Math.round(item.completion_pct * 100),
            label: formatWeekLabel(item.week_start),
          })),
        );
      })
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <WidgetSkeleton className="min-h-[200px]" lines={4} />;
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">Couldn&apos;t load weekly data.</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">No weekly data yet.</p>
      </div>
    );
  }

  return (
    <motion.div
      className="glass-card p-4 rounded-2xl"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h3 className="text-sm font-semibold text-charcoal mb-3">
        Weekly completion
      </h3>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="weeklyGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--color-sage)"
                  stopOpacity={0.4}
                />
                <stop
                  offset="100%"
                  stopColor="var(--color-sage)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: "var(--color-river)" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: "var(--color-river)" }}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Area
              type="monotone"
              dataKey="pct"
              stroke="var(--color-sage)"
              strokeWidth={2}
              fill="url(#weeklyGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

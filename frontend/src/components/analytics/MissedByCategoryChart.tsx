import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { type AnalyticsMissedByCategoryItem, api } from "~/utils/api";
import { WidgetSkeleton } from "./WidgetSkeleton";

const CATEGORY_COLORS = [
  "var(--color-sage)",
  "var(--color-terracotta)",
  "var(--color-river)",
];

export function MissedByCategoryChart() {
  const [data, setData] = useState<AnalyticsMissedByCategoryItem[] | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api
      .analyticsMissedByCategory()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return <WidgetSkeleton className="min-h-[180px]" lines={4} />;
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">
          Couldn&apos;t load missed tasks data.
        </p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">No missed tasks by category.</p>
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
        Missed by category
      </h3>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 8, left: 60, bottom: 4 }}
          >
            <XAxis
              type="number"
              tick={{ fontSize: 10, fill: "var(--color-river)" }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="category"
              width={56}
              tick={{ fontSize: 10, fill: "var(--color-river)" }}
              tickLine={false}
            />
            <Bar dataKey="missed_count" radius={[0, 4, 4, 0]}>
              {data.map((item, index) => (
                <Cell
                  key={item.category}
                  fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

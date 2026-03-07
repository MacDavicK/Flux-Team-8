import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { type AnalyticsHeatmapItem, api } from "~/utils/api";
import { WidgetSkeleton } from "./WidgetSkeleton";

const ROWS = 7;
const COLS = 53;

function toDateKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function getColorClass(count: number): string {
  if (count <= 0) return "bg-river/20";
  if (count === 1) return "bg-sage/40";
  if (count <= 3) return "bg-sage/60";
  return "bg-sage";
}

export function ActivityHeatmap() {
  const [data, setData] = useState<AnalyticsHeatmapItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    api
      .analyticsHeatmap()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e : new Error(String(e))))
      .finally(() => setIsLoading(false));
  }, []);

  const { grid, monthLabels } = useMemo(() => {
    const map = new Map<string, number>();
    if (data) {
      for (const item of data) {
        map.set(item.day, item.done_count);
      }
    }
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - 364);
    const cells: { count: number }[][] = [];
    for (let col = 0; col < COLS; col++) {
      cells[col] = [];
      for (let row = 0; row < ROWS; row++) {
        const dayOffset = col * 7 + row;
        const d = new Date(start);
        d.setDate(d.getDate() + dayOffset);
        if (d > end) {
          cells[col][row] = { count: -1 };
          continue;
        }
        const key = toDateKey(d);
        const count = map.get(key) ?? 0;
        cells[col][row] = { count };
      }
    }
    const monthLabels: { col: number; label: string }[] = [];
    let lastMonth = -1;
    for (let col = 0; col < COLS; col++) {
      const d = new Date(start);
      d.setDate(d.getDate() + col * 7);
      const m = d.getMonth();
      if (m !== lastMonth) {
        lastMonth = m;
        monthLabels.push({
          col,
          label: d.toLocaleDateString("en-US", { month: "short" }),
        });
      }
    }
    return { grid: cells, monthLabels };
  }, [data]);

  if (isLoading) {
    return <WidgetSkeleton className="min-h-[140px]" lines={5} />;
  }

  if (error) {
    return (
      <div className="glass-card p-4">
        <p className="text-sm text-river/80">
          Couldn&apos;t load activity data.
        </p>
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
      <h3 className="text-sm font-semibold text-charcoal mb-2">Activity</h3>
      <div className="overflow-x-auto">
        <div
          className="grid gap-0.5 mb-1"
          style={{
            gridTemplateColumns: `repeat(${COLS}, minmax(4px, 1fr))`,
            minWidth: 280,
          }}
        >
          {monthLabels.map(({ col, label }) => (
            <span
              key={`${col}-${label}`}
              className="text-[10px] text-river/70 col-start-[unset]"
              style={{ gridColumn: col + 1 }}
            >
              {label}
            </span>
          ))}
        </div>
        <div
          className="grid gap-0.5"
          style={{
            gridTemplateColumns: `repeat(${COLS}, minmax(4px, 1fr))`,
            gridTemplateRows: `repeat(${ROWS}, 10px)`,
            width: "100%",
            minWidth: 280,
          }}
        >
          {Array.from({ length: ROWS }, (_, rowIndex) =>
            Array.from({ length: COLS }, (_, colIndex) => {
              const cell = grid[colIndex]?.[rowIndex] ?? { count: -1 };
              const cellKey = `heatmap-${rowIndex}-${colIndex}`;
              return (
                <div
                  key={cellKey}
                  className={`w-full h-full rounded-sm min-w-[4px] ${cell.count < 0 ? "invisible" : getColorClass(cell.count)}`}
                  title={
                    cell.count >= 0
                      ? `${cell.count} task${cell.count !== 1 ? "s" : ""} done`
                      : undefined
                  }
                />
              );
            }),
          ).flat()}
        </div>
      </div>
    </motion.div>
  );
}

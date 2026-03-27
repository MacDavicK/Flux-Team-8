import { motion } from "framer-motion";

interface CategoryData {
  name: string;
  count: number;
  percent: number;
  color: string;
}

interface FocusDistributionProps {
  categories: CategoryData[];
  className?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  work: "#5C7C66",
  personal: "#C27D66",
  health: "#8A8F8B",
  fitness: "#8A8F8B",
  finance: "#7B8C6E",
  education: "#6E7B8C",
  social: "#8C6E7B",
};

const DEFAULT_COLOR = "#A0A89C";

export function FocusDistribution({
  categories = [],
  className,
}: FocusDistributionProps) {
  if (categories.length === 0) return null;

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h3 className="text-river text-xs font-semibold uppercase tracking-wider mb-3">
        Focus Distribution
      </h3>

      <div className="glass-card p-6 flex flex-col gap-4">
        {categories.map((category, index) => (
          <div key={category.name}>
            <div className="flex justify-between items-baseline mb-1.5">
              <span className="text-charcoal text-sm capitalize flex items-center gap-2">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: category.color }}
                />
                {category.name}
              </span>
              <span className="text-river text-xs tabular-nums">
                {category.percent}%
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-stone-200/60 overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: category.color }}
                initial={{ width: 0 }}
                animate={{ width: `${category.percent}%` }}
                transition={{
                  delay: index * 0.08,
                  duration: 0.6,
                  ease: "easeOut",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export { CATEGORY_COLORS, DEFAULT_COLOR };
export type { CategoryData };

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

      <div className="glass-card p-6">
        {/* Overlapping circles visualization */}
        <div className="relative h-40 flex items-center justify-center">
          {categories.map((category, index) => {
            const size = 60 + category.percent * 0.8;
            const offset = index * 15;

            return (
              <motion.div
                key={category.name}
                className="absolute rounded-full mix-blend-multiply"
                style={{
                  width: size,
                  height: size,
                  backgroundColor: category.color,
                  opacity: 0.6,
                  left: `calc(50% - ${size / 2}px + ${(index - 1) * 20}px)`,
                  top: `calc(50% - ${size / 2}px + ${offset}px)`,
                }}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 0.6 }}
                transition={{
                  delay: index * 0.2,
                  type: "spring",
                  stiffness: 200,
                  damping: 20,
                }}
              />
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap justify-center gap-4 mt-4">
          {categories.map((category) => (
            <div key={category.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color }}
              />
              <span className="text-charcoal text-sm capitalize">
                {category.name}
              </span>
              <span className="text-river text-xs">
                ({Math.round(category.percent)}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export { CATEGORY_COLORS, DEFAULT_COLOR };
export type { CategoryData };

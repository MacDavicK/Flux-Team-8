import { motion } from "framer-motion";

interface FocusDistributionProps {
  work: number;
  personal: number;
  health: number;
  className?: string;
}

export function FocusDistribution({
  work,
  personal,
  health,
  className,
}: FocusDistributionProps) {
  const total = work + personal + health;
  const workPercent = (work / total) * 100;
  const personalPercent = (personal / total) * 100;
  const healthPercent = (health / total) * 100;

  const categories = [
    { name: "Work", value: work, percent: workPercent, color: "#5C7C66" },
    {
      name: "Personal",
      value: personal,
      percent: personalPercent,
      color: "#C27D66",
    },
    { name: "Health", value: health, percent: healthPercent, color: "#8A8F8B" },
  ];

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
        <div className="flex justify-center gap-4 mt-4">
          {categories.map((category) => (
            <div key={category.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: category.color }}
              />
              <span className="text-charcoal text-sm">{category.name}</span>
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

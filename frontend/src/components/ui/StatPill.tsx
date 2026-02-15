import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface StatPillProps {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  className?: string;
}

export function StatPill({ icon, value, label, className }: StatPillProps) {
  return (
    <motion.div
      className={cn(
        "glass-bubble px-4 py-3 flex items-center gap-3",
        className,
      )}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="text-sage">{icon}</div>
      <div className="flex flex-col">
        <span className="text-xl font-bold text-charcoal">{value}</span>
        <span className="text-xs text-river uppercase tracking-wide">
          {label}
        </span>
      </div>
    </motion.div>
  );
}

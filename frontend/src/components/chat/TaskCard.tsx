import { motion } from "framer-motion";
import { Clock, Plus } from "lucide-react";
import { cn } from "~/utils/cn";

interface TaskCardProps {
  title: string;
  duration?: string;
  onAdd?: () => void;
  className?: string;
}

export function TaskCard({ title, duration, onAdd, className }: TaskCardProps) {
  return (
    <motion.div
      className={cn(
        "glass-bubble p-3 flex items-center gap-3",
        "border-l-4 border-l-sage",
        className,
      )}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02 }}
    >
      <div className="flex-1 min-w-0">
        <p className="text-charcoal text-sm font-medium truncate">{title}</p>
        {duration && (
          <div className="flex items-center gap-1 text-river text-xs mt-1">
            <Clock className="w-3 h-3" />
            <span>{duration}</span>
          </div>
        )}
      </div>

      <motion.button
        type="button"
        onClick={onAdd}
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          "bg-sage text-white flex-shrink-0",
          "hover:bg-sage-dark active:scale-95 transition-colors",
        )}
        whileTap={{ scale: 0.9 }}
        whileHover={{ rotate: 90 }}
        transition={{ duration: 0.2 }}
      >
        <Plus className="w-4 h-4" />
      </motion.button>
    </motion.div>
  );
}

import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

interface EventPebbleProps {
  title: string;
  time?: string;
  duration?: string;
  isOverdue?: boolean;
  onClick?: () => void;
  onDragStart?: () => void;
}

export function EventPebble({
  title,
  time,
  duration,
  isOverdue = false,
  onClick,
  onDragStart,
}: EventPebbleProps) {
  return (
    <motion.div
      layoutId={`event-${title}`}
      onClick={onClick}
      onDragStart={onDragStart}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.2}
      whileDrag={{ scale: 1.02, cursor: "grabbing" }}
      whileTap={{ scale: 0.98, cursor: "grab" }}
      className={cn(
        "event-pebble p-4 mb-3 cursor-pointer touch-manipulation",
        "transition-shadow duration-200",
        isOverdue && "shadow-[0_0_15px_rgba(194,125,102,0.4)]",
      )}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <div className="flex flex-col gap-1">
        <h3 className="text-charcoal font-semibold text-body">{title}</h3>
        <div className="flex items-center gap-2 text-river text-sm">
          {time && <span>{time}</span>}
          {duration && (
            <>
              <span>•</span>
              <span>{duration}</span>
            </>
          )}
        </div>
      </div>

      {isOverdue && (
        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-terracotta animate-pulse" />
      )}
    </motion.div>
  );
}

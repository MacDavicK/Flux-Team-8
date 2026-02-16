import { motion } from "framer-motion";
import type { EventType } from "~/types/event";
import { cn } from "~/utils/cn";

interface TimelineEventProps {
  title: string;
  description: string;
  time: string;
  period: string;
  type: EventType;
  avatars?: string[];
  isLast?: boolean;
}

export function TimelineEvent({
  title,
  description,
  time,
  period,
  type,
}: TimelineEventProps) {
  const typeClasses = {
    sage: "glass-pebble-sage rounded-tl-md",
    terra: "glass-pebble-terra rounded-bl-md",
    stone: "glass-pebble-stone rounded-tr-md",
  };

  return (
    <div className="flex gap-4 group">
      <div className="flex flex-col items-center pt-2 w-12 shrink-0">
        <span className="text-xs font-semibold text-river">{time}</span>
        <span className="text-[10px] text-river/60">{period}</span>
      </div>
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        whileHover={{ scale: 1.02 }}
        className={cn(
          "flex-1 p-5 rounded-[1.5rem] transition-transform",
          typeClasses[type],
        )}
      >
        <h3 className="text-lg font-semibold text-charcoal mb-1 pt-0">
          {title}
        </h3>
        <p className="text-sm text-river leading-snug">{description}</p>
      </motion.div>
    </div>
  );
}

export type { EventType };

import { motion } from "framer-motion";
import { cn } from "~/utils/cn";

export type EventType = "sage" | "terra" | "stone";

interface TimelineEventProps {
  title: string;
  description: string;
  time: string;
  period: string;
  type: EventType;
  avatars?: string[];
  isLast?: boolean;
  status?: string;
  goalName?: string;
  onClick?: () => void;
}

export function TimelineEvent({
  title,
  description,
  time,
  period,
  type,
  status,
  goalName,
  onClick,
}: TimelineEventProps) {
  const typeClasses = {
    sage: "glass-pebble-sage rounded-tl-md",
    terra: "glass-pebble-terra rounded-bl-md",
    stone: "glass-pebble-stone rounded-tr-md",
  };

  // Status-based left border accent
  const statusBorder =
    status === "missed"
      ? "border-l-4 border-l-red-400"
      : status === "done" || status === "completed"
        ? "border-l-4 border-l-green-400"
        : "";

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
        onClick={onClick}
        className={cn(
          "flex-1 p-5 rounded-[1.5rem] transition-transform relative",
          typeClasses[type],
          statusBorder,
          onClick && "cursor-pointer",
        )}
      >
        <h3 className="text-lg font-semibold text-charcoal mb-1 pt-0">
          {title}
        </h3>
        <p className="text-sm text-river leading-snug">{description}</p>
        {goalName && (
          <p className="text-xs text-river/50 mt-2 font-medium">{goalName}</p>
        )}
      </motion.div>
    </div>
  );
}

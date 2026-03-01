import { motion } from "framer-motion";
import { Shuffle } from "lucide-react";
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
  isDrifted?: boolean;
  eventId?: string;
  onShuffleClick?: (eventId: string, taskTitle: string) => void;
}

export function TimelineEvent({
  title,
  description,
  time,
  period,
  type,
  avatars,
  isDrifted,
  eventId,
  onShuffleClick,
}: TimelineEventProps) {
  const typeClasses = {
    sage: "glass-pebble-sage rounded-tl-md",
    terra: "glass-pebble-terra rounded-bl-md",
    stone: "glass-pebble-stone rounded-tr-md",
  };

  const showShuffle = isDrifted && eventId && onShuffleClick;

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
          "flex-1 p-5 rounded-[1.5rem] transition-transform relative",
          typeClasses[type],
          isDrifted && "ring-2 ring-terracotta/50 shadow-lg shadow-terracotta/10",
        )}
      >
        {isDrifted && (
          <span
            className="absolute top-4 right-4 w-2 h-2 rounded-full bg-terracotta animate-pulse"
            aria-hidden
          />
        )}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-charcoal mb-1 pt-0">
              {title}
            </h3>
            <p className="text-sm text-river leading-snug">{description}</p>
          </div>
          {showShuffle && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onShuffleClick(eventId, title);
              }}
              className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium bg-terracotta/20 text-terracotta hover:bg-terracotta/30 transition-colors flex items-center gap-1.5"
            >
              <Shuffle className="w-3.5 h-3.5" />
              Shuffle?
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}

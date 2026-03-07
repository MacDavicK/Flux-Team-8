import type { TimelineEvent as TimelineEventType } from "~/types";
import { TimelineEvent } from "./TimelineEvent";

interface FlowTimelineProps {
  events: TimelineEventType[];
  onTaskClick?: (event: TimelineEventType) => void;
}

export function FlowTimeline({ events, onTaskClick }: FlowTimelineProps) {
  return (
    <div className="flex-1 relative overflow-hidden">
      <div className="px-6 pt-4 pb-2">
        <h2 className="text-xs font-bold text-river uppercase tracking-widest">
          Events
        </h2>
      </div>
      <div className="absolute inset-0 overflow-y-auto scrollbar-hide px-6 space-y-4 pb-32 pt-10">
        {events.map((event, _index) => (
          <div key={event.id} className={event.isPast && event.status !== "missed" ? "opacity-70" : ""}>
            <TimelineEvent
              title={event.title}
              description={event.description}
              time={event.time}
              period={event.period}
              type={event.type}
              avatars={event.avatars}
              status={event.status}
              goalName={event.goalName}
              onClick={onTaskClick ? () => onTaskClick(event) : undefined}
            />
          </div>
        ))}
        <div className="h-24"></div>
      </div>

      {/* Scroll Fade Overlay */}
      <div className="absolute bottom-0 left-0 w-full h-32 bg-bottom-fade pointer-events-none z-10" />
    </div>
  );
}

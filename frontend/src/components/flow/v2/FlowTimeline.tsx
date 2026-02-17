import type { TimelineEvent as TimelineEventType } from "~/types";
import { TimelineEvent } from "./TimelineEvent";

interface FlowTimelineProps {
  events: TimelineEventType[];
}

export function FlowTimeline({ events }: FlowTimelineProps) {
  return (
    <div className="flex-1 relative overflow-hidden">
      <div className="absolute inset-0 overflow-y-auto scrollbar-hide px-6 space-y-4 pb-32">
        {events.map((event, index) => (
          <div key={event.id} className={event.isPast ? "opacity-70" : ""}>
            <TimelineEvent
              title={event.title}
              description={event.description}
              time={event.time}
              period={event.period}
              type={event.type}
              avatars={event.avatars}
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

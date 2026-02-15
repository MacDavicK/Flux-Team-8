import { TimelineEvent, type EventType } from "./TimelineEvent";

interface Event {
  id: string;
  title: string;
  description: string;
  time: string;
  period: string;
  type: EventType;
  avatars?: string[];
  isPast?: boolean;
}

interface FlowTimelineProps {
  events: Event[];
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
            {/* Simple logic for "Now" indicator - could be more dynamic */}
            {index === 1 && (
              <div className="relative py-4 flex items-center justify-end">
                <div className="absolute left-0 w-full h-[1px] bg-now-line"></div>
                <div className="flex flex-col items-center w-12 shrink-0 relative z-10 mr-0">
                  <span className="text-xs font-bold text-sage bg-stone/80 backdrop-blur px-2 py-0.5 rounded-full shadow-sm border border-sage/10">
                    Now
                  </span>
                </div>
              </div>
            )}
          </div>
        ))}
        <div className="h-24"></div>
      </div>

      {/* Scroll Fade Overlay */}
      <div className="absolute bottom-0 left-0 w-full h-32 bg-bottom-fade pointer-events-none z-10" />
    </div>
  );
}

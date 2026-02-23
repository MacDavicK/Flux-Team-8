import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import { NegotiationModal } from "~/components/modals/RescheduleModal";

type TimelineEvent = {
  id: string;
  title: string;
  description: string;
  time: string;
  period: string;
  type: "sage" | "terra" | "stone";
  isPast?: boolean;
  state?: "scheduled" | "drifted";
};

// Sample v2 data
const initialEvents: TimelineEvent[] = [
  {
    id: "1",
    title: "Deep Work: Strategy",
    description: "Focus block for Q4 roadmap planning.",
    time: "10:00",
    period: "AM",
    type: "sage",
  },
  {
    id: "2",
    title: "Coffee w/ Team",
    description: "Discussion about the offsite.",
    time: "11:30",
    period: "AM",
    type: "terra",
  },
  {
    id: "3",
    title: "Client Review",
    description: "Reviewing final mockups for Flux.",
    time: "01:00",
    period: "PM",
    type: "stone",
  },
  {
    id: "4",
    title: "Pick up dry cleaning",
    description: "",
    time: "03:30",
    period: "PM",
    type: "stone",
    isPast: true,
  },
  {
    id: "5",
    title: "Gym Session",
    description: "",
    time: "04:30",
    period: "PM",
    type: "stone",
    isPast: true,
    state: "drifted",
  },
];

const sampleTasks = [
  { id: "1", title: "Email Sarah regarding brand", completed: false },
  { id: "2", title: "Sketch logo concepts", completed: false },
  { id: "3", title: "Update documentation", completed: true },
];

export const Route = createFileRoute("/")({
  component: FlowPage,
});

function formatTimeFromISO(iso: string): { time: string; period: string } {
  const d = new Date(iso);
  const hours = d.getHours();
  const mins = d.getMinutes();
  const period = hours >= 12 ? "PM" : "AM";
  const h = hours % 12 || 12;
  const time = `${h.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
  return { time, period };
}

function FlowPage() {
  const [events, setEvents] = useState<TimelineEvent[]>(initialEvents);
  const [rescheduleModal, setRescheduleModal] = useState<{
    isOpen: boolean;
    eventId: string;
    taskTitle: string;
  }>({ isOpen: false, eventId: "", taskTitle: "" });

  const handleReschedule = (result: {
    action: string;
    newState: string;
    message: string;
    newStart?: string;
    newEnd?: string;
  }) => {
    if (result.action === "skip") {
      setEvents((prev) =>
        prev.filter((e) => e.id !== rescheduleModal.eventId),
      );
    } else if (result.newStart != null && result.newEnd != null) {
      const { time, period } = formatTimeFromISO(result.newStart);
      setEvents((prev) =>
        prev.map((e) =>
          e.id === rescheduleModal.eventId
            ? { ...e, time, period, state: "scheduled" as const }
            : e,
        ),
      );
    }
    setRescheduleModal({ isOpen: false, eventId: "", taskTitle: "" });
  };

  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader />

      <TaskRail tasks={sampleTasks} />

      <FlowTimeline
        events={events}
        onShuffle={(eventId, taskTitle) =>
          setRescheduleModal({ isOpen: true, eventId, taskTitle })
        }
      />

      <BottomNav />

      <NegotiationModal
        isOpen={rescheduleModal.isOpen}
        onClose={() =>
          setRescheduleModal({ isOpen: false, eventId: "", taskTitle: "" })
        }
        eventId={rescheduleModal.eventId}
        taskTitle={rescheduleModal.taskTitle}
        onReschedule={handleReschedule}
      />
    </div>
  );
}

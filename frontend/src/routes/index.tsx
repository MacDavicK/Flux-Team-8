import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import { RescheduleModal } from "~/components/modals/RescheduleModal";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";

// Sample v2 data
const sampleEvents = [
  {
    id: "1",
    title: "Deep Work: Strategy",
    description: "Focus block for Q4 roadmap planning.",
    time: "10:00",
    period: "AM",
    type: "sage" as const,
  },
  {
    id: "2",
    title: "Coffee w/ Team",
    description: "Discussion about the offsite.",
    time: "11:30",
    period: "AM",
    type: "terra" as const,
  },
  {
    id: "3",
    title: "Client Review",
    description: "Reviewing final mockups for Flux.",
    time: "01:00",
    period: "PM",
    type: "stone" as const,
  },
  {
    id: "4",
    title: "Pick up dry cleaning",
    description: "",
    time: "03:30",
    period: "PM",
    type: "stone" as const,
    isPast: true,
  },
  {
    id: "5",
    title: "Gym Session",
    description: "",
    time: "04:30",
    period: "PM",
    type: "stone" as const,
    isPast: true,
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

function FlowPage() {
  const [rescheduleModal, setRescheduleModal] = useState<{
    isOpen: boolean;
    taskTitle: string;
  }>({ isOpen: false, taskTitle: "" });

  const handleReschedule = (option: string) => {
    console.log("Rescheduled to:", option);
    setRescheduleModal({ isOpen: false, taskTitle: "" });
  };

  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader />

      <TaskRail tasks={sampleTasks} />

      <FlowTimeline events={sampleEvents} />

      <BottomNav />

      <RescheduleModal
        isOpen={rescheduleModal.isOpen}
        onClose={() => setRescheduleModal({ isOpen: false, taskTitle: "" })}
        taskTitle={rescheduleModal.taskTitle}
        onReschedule={handleReschedule}
      />
    </div>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import { RescheduleModal } from "~/components/modals/RescheduleModal";
import { fetchTimelineTasks, type Task } from "~/utils/api";
import type { EventType } from "~/components/flow/v2/TimelineEvent";

// Fallback tasks when API is unavailable (e.g. backend not running)
const sampleTasks = [
  { id: "1", title: "Email Sarah regarding brand", completed: false },
  { id: "2", title: "Sketch logo concepts", completed: false },
  { id: "3", title: "Update documentation", completed: true },
];

function taskToEvent(task: Task): {
  id: string;
  title: string;
  description: string;
  time: string;
  period: string;
  type: EventType;
  isPast?: boolean;
  isDrifted: boolean;
  eventId: string;
} {
  const start = task.start_time ? new Date(task.start_time) : new Date();
  const hours = start.getUTCHours();
  const mins = start.getUTCMinutes();
  const isPm = hours >= 12;
  const hour12 = hours % 12 || 12;
  const time = `${hour12.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
  const period = isPm ? "PM" : "AM";
  const now = new Date();
  const isPast = start < now;
  const isDrifted = task.state === "drifted";
  return {
    id: task.id,
    title: task.title,
    description: "",
    time,
    period,
    type: isDrifted ? "terra" : "stone",
    isPast,
    isDrifted,
    eventId: task.id,
  };
}

export const Route = createFileRoute("/")({
  component: FlowPage,
});

function FlowPage() {
  const [events, setEvents] = useState<ReturnType<typeof taskToEvent>[]>([]);
  const [loading, setLoading] = useState(true);
  const [rescheduleModal, setRescheduleModal] = useState<{
    isOpen: boolean;
    eventId: string;
    taskTitle: string;
  }>({ isOpen: false, eventId: "", taskTitle: "" });

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const tasks = await fetchTimelineTasks();
      setEvents(tasks.map(taskToEvent));
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const openShuffle = (eventId: string, taskTitle: string) => {
    setRescheduleModal({ isOpen: true, eventId, taskTitle });
  };

  const closeModal = () => {
    setRescheduleModal({ isOpen: false, eventId: "", taskTitle: "" });
  };

  const handleRescheduleDone = () => {
    closeModal();
    loadTasks();
  };

  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader />

      <TaskRail tasks={sampleTasks} />

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-river text-sm">
          Loading schedule…
        </div>
      ) : (
        <FlowTimeline
          events={events}
          onShuffleClick={openShuffle}
        />
      )}

      <BottomNav />

      <RescheduleModal
        isOpen={rescheduleModal.isOpen}
        eventId={rescheduleModal.eventId}
        taskTitle={rescheduleModal.taskTitle}
        onClose={closeModal}
        onRescheduleDone={handleRescheduleDone}
      />
    </div>
  );
}

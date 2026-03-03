import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import type { EventType } from "~/components/flow/v2/TimelineEvent";
import { RescheduleModal } from "~/components/modals/RescheduleModal";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import type { TaskRailItem } from "~/types";
import { api, type Task } from "~/utils/api";

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
  const startAt =
    task.start_time ??
    (task as { scheduled_at?: string }).scheduled_at ??
    new Date().toISOString();
  const start = new Date(startAt);
  const hours = start.getHours();
  const mins = start.getMinutes();
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

function taskToRailItem(task: Task): TaskRailItem {
  const status = (task as { status?: string }).status ?? task.state;
  return {
    id: task.id,
    title: task.title,
    completed: status === "done",
  };
}

export const Route = createFileRoute("/")({
  component: FlowPage,
});

function FlowPage() {
  const [events, setEvents] = useState<ReturnType<typeof taskToEvent>[]>([]);
  const [railTasks, setRailTasks] = useState<TaskRailItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [rescheduleModal, setRescheduleModal] = useState<{
    isOpen: boolean;
    eventId: string;
    taskTitle: string;
  }>({ isOpen: false, eventId: "", taskTitle: "" });

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const [timelineTasks, todayTasks] = await Promise.all([
        api.timelineTasks().catch(() => [] as Task[]),
        api.todayTasks().catch(() => [] as Task[]),
      ]);
      setEvents(timelineTasks.map(taskToEvent));
      setRailTasks(todayTasks.map(taskToRailItem));
    } catch {
      setEvents([]);
      setRailTasks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleCompleteTask = useCallback(
    (taskId: string) => {
      api
        .completeTask(taskId)
        .then(() => loadTasks())
        .catch(() => {});
    },
    [loadTasks],
  );

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

      <TaskRail tasks={railTasks} onComplete={handleCompleteTask} />

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-river text-sm">
          Loading schedule…
        </div>
      ) : (
        <FlowTimeline events={events} onShuffleClick={openShuffle} />
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

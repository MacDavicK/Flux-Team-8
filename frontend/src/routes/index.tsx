import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import { RescheduleModal } from "~/components/modals/RescheduleModal";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import type { TasksResponse } from "~/mocks/tasksHandlers";
import type { TaskRailItem, TimelineEvent } from "~/types";

export const Route = createFileRoute("/")({
  component: FlowPage,
});

function FlowPage() {
  const [data, setData] = useState<{
    events: TimelineEvent[];
    tasks: TaskRailItem[];
  }>({ events: [], tasks: [] });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch("/api/tasks")
      .then((res) => res.json() as Promise<TasksResponse>)
      .then((data) => {
        setData({ events: data.events, tasks: data.tasks });
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Failed to fetch tasks:", error);
        setIsLoading(false);
      });
  }, []);

  const [rescheduleModal, setRescheduleModal] = useState<{
    isOpen: boolean;
    taskTitle: string;
  }>({ isOpen: false, taskTitle: "" });

  const handleReschedule = (option: string) => {
    console.log("Rescheduled to:", option);
    setRescheduleModal({ isOpen: false, taskTitle: "" });
  };

  if (isLoading) {
    return (
      <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
        <AmbientBackground />
        <LoadingState />
        <BottomNav />
      </div>
    );
  }

  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader />

      <TaskRail tasks={data.tasks} />

      <FlowTimeline events={data.events} />

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

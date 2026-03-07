import * as Sentry from "@sentry/react";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { serverGetMe } from "~/lib/authServerFns";
import { useState, useEffect } from "react";
import { z } from "zod";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskRail } from "~/components/flow/v2/TaskRail";
import { TaskDetailSheet } from "~/components/modals/TaskDetailSheet";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { useAuth } from "~/contexts/AuthContext";
import { setInMemoryToken } from "~/lib/apiClient";
import { tasksService } from "~/services/TasksService";
import { debugSsrLog, isClient } from "~/utils/env";
import { EventType, type TaskRailItem, type TimelineEvent } from "~/types";

function FlowPagePending() {
  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden items-center justify-center">
      <AmbientBackground />
      <LoadingState />
    </div>
  );
}

export const Route = createFileRoute("/")({
  pendingComponent: FlowPagePending,
  pendingMs: 0,
  validateSearch: z.object({
    complete_task_id: z.string().optional(),
    missed_task_id: z.string().optional(),
  }),
  loader: async () => {
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    if (!user.onboarded) throw redirect({ to: "/chat" });

    const rawTasks: { [key: string]: unknown }[] = await (async () => {
      if (isClient()) {
        // Hydrate the in-memory token before calling apiFetch-based services.
        // The loader runs before AuthContext.useEffect has a chance to set it.
        setInMemoryToken(token);
        return tasksService.getTodayTasks().catch((e) => { Sentry.captureException(e); return []; });
      }
      const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
      return fetch(`${backendUrl}/api/v1/tasks/today`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .catch((e) => { Sentry.captureException(e); return []; });
    })();

    const events: TimelineEvent[] = [];
    const tasks: TaskRailItem[] = [];
    for (const t of rawTasks) {
      const { railItem, event } = mapTaskToDisplayTypes(t);
      const hasTime = Boolean(t.scheduled_at ?? t.scheduled_time ?? t.time ?? "");
      if (hasTime) {
        events.push(event);
      } else {
        tasks.push(railItem);
      }
    }
    const data = { user, events, tasks };
    debugSsrLog("/ (FlowPage)", data);
    return data;
  },
  component: FlowPage,
});

// Map a raw task object from /api/v1/tasks/today to UI display types.
// The backend shape is not yet strictly typed, so we defensively cast.
function mapTaskToDisplayTypes(task: { [key: string]: unknown }): {
  railItem: TaskRailItem;
  event: TimelineEvent;
} {
  const id = String(task.id ?? "");
  const title = String(task.title ?? "Untitled");
  const description = String(task.description ?? "");
  const status = String(task.status ?? "pending");
  // Backend uses "done"; spec uses "completed" — accept both.
  const isDone = status === "done" || status === "completed";
  const isPast = isDone || status === "missed";

  // Best-effort time parsing from scheduled_at (ISO 8601) or legacy time fields
  const scheduledAt = task.scheduled_at as string | null | undefined;
  const rawTime = scheduledAt
    ? new Date(scheduledAt).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false })
    : String(task.scheduled_time ?? task.time ?? "");
  let time = rawTime;
  let period: "AM" | "PM" = "AM";
  if (rawTime.includes(":")) {
    const [h] = rawTime.split(":").map(Number);
    period = h >= 12 ? "PM" : "AM";
    const displayHour = h > 12 ? h - 12 : h === 0 ? 12 : h;
    time = `${String(displayHour).padStart(2, "0")}:${rawTime.split(":")[1]}`;
  }

  const category = String(task.category ?? "");
  let eventType = EventType.STONE;
  if (category === "work") eventType = EventType.SAGE;
  else if (category === "personal") eventType = EventType.TERRA;

  const durationMinutes = typeof task.duration_minutes === "number" ? task.duration_minutes : undefined;

  return {
    railItem: { id, title, completed: isDone },
    event: { id, title, description, time, period, type: eventType, isPast, status, durationMinutes },
  };
}

function getGreeting(name?: string): string {
  const hour = new Date().getHours();
  const salutation = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation;
}

function FlowPage() {
  const { events: initialEvents, tasks: initialTasks, user: loaderUser } = Route.useLoaderData();
  const { complete_task_id, missed_task_id } = Route.useSearch();
  const { user } = useAuth();
  const [data, setData] = useState<{ events: TimelineEvent[]; tasks: TaskRailItem[] }>({
    events: initialEvents,
    tasks: initialTasks,
  });

  const displayName = user?.name ?? loaderUser.name;

  const handleAddTodo = (title: string) => {
    const tempId = `temp-${Date.now()}`;
    setData((prev) => ({
      ...prev,
      tasks: [...prev.tasks, { id: tempId, title, completed: false }],
    }));

    tasksService.addTodo(title).then((result) => {
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.map((t) =>
          t.id === tempId ? { ...t, id: result.task_id } : t,
        ),
      }));
    }).catch((error) => {
      Sentry.captureException(error, { extra: { title } });
      setData((prev) => ({
        ...prev,
        tasks: prev.tasks.filter((t) => t.id !== tempId),
      }));
    });
  };

  const handleComplete = (taskId: string) => {
    // Optimistic update — mark done immediately in local state.
    setData((prev) => ({
      events: prev.events.map((e) =>
        e.id === taskId ? { ...e, isPast: true } : e,
      ),
      tasks: prev.tasks.map((t) =>
        t.id === taskId ? { ...t, completed: true } : t,
      ),
    }));

    tasksService.completeTask(taskId).catch((error) => {
      Sentry.captureException(error, { extra: { taskId } });
      // Revert optimistic update on error.
      setData((prev) => ({
        events: prev.events.map((e) =>
          e.id === taskId ? { ...e, isPast: false } : e,
        ),
        tasks: prev.tasks.map((t) =>
          t.id === taskId ? { ...t, completed: false } : t,
        ),
      }));
    });
  };

  const navigate = useNavigate();
  const [selectedTask, setSelectedTask] = useState<TimelineEvent | null>(null);

  const handleMissed = (taskId: string) => {
    setData((prev) => ({
      ...prev,
      events: prev.events.map((e) =>
        e.id === taskId ? { ...e, status: "missed", isPast: true } : e,
      ),
    }));
    tasksService.missedTask(taskId).catch((error: unknown) => {
      Sentry.captureException(error, { extra: { taskId } });
    });
  };

  // Handle deep-links from push notification actions (done / missed)
  useEffect(() => {
    if (complete_task_id) {
      handleComplete(complete_task_id);
      window.history.replaceState(null, "", "/");
    } else if (missed_task_id) {
      handleMissed(missed_task_id);
      window.history.replaceState(null, "", "/");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative w-full max-w-md mx-auto h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader greeting={getGreeting(displayName)} />

      <TaskRail tasks={data.tasks} onComplete={handleComplete} onAddTodo={handleAddTodo} />

      <FlowTimeline
        events={data.events}
        onTaskClick={(event) => setSelectedTask(event)}
      />

      <BottomNav />

      <TaskDetailSheet
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
        onComplete={(taskId) => {
          handleComplete(taskId);
          setSelectedTask(null);
        }}
        onMissed={(taskId) => {
          handleMissed(taskId);
          setSelectedTask(null);
        }}
        onReschedule={(taskId, taskTitle) => {
          setSelectedTask(null);
          navigate({
            to: "/chat",
            search: { reschedule_task_id: taskId, task_name: taskTitle },
          });
        }}
      />
    </div>
  );
}

import * as Sentry from "@sentry/react";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { z } from "zod";
import { DateHeader } from "~/components/flow/v2/DateHeader";
import { FlowTimeline } from "~/components/flow/v2/FlowTimeline";
import { TaskDetailSheet } from "~/components/modals/TaskDetailSheet";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { useAuth } from "~/contexts/AuthContext";
import { setInMemoryToken } from "~/lib/apiClient";
import { serverGetMe } from "~/lib/authServerFns";
import { tasksService } from "~/services/TasksService";
import { EventType, type TimelineEvent } from "~/types";
import { debugSsrLog, isClient } from "~/utils/env";

function FlowPagePending() {
  return (
    <div className="relative w-full h-screen flex flex-col overflow-hidden items-center justify-center">
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
    date: z.string().optional(),
  }),
  loader: async ({ location }) => {
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    if (!user.onboarded) throw redirect({ to: "/chat" });

    const searchDate = (location.search as Record<string, string | undefined>)
      .date;
    const dateParam = searchDate
      ? `?date=${encodeURIComponent(searchDate)}`
      : "";

    const rawTasks: { [key: string]: unknown }[] = await (async () => {
      if (isClient()) {
        // Hydrate the in-memory token before calling apiFetch-based services.
        // The loader runs before AuthContext.useEffect has a chance to set it.
        setInMemoryToken(token);
        return tasksService.getTasks(searchDate).catch((e) => {
          Sentry.captureException(e);
          return [];
        });
      }
      const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
      return fetch(`${backendUrl}/api/v1/tasks${dateParam}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .catch((e) => {
          Sentry.captureException(e);
          return [];
        });
    })();

    const events: TimelineEvent[] = [];
    for (const t of rawTasks) {
      const event = mapTaskToDisplayTypes(t);
      const hasTime = Boolean(
        t.scheduled_at ?? t.scheduled_time ?? t.time ?? "",
      );
      if (hasTime) {
        events.push(event);
      }
    }
    const data = { user, events, selectedDate: searchDate ?? null };
    debugSsrLog("/ (FlowPage)", data);
    return data;
  },
  component: FlowPage,
});

// Map a raw task object from /api/v1/tasks to a TimelineEvent.
// The backend shape is not yet strictly typed, so we defensively cast.
function mapTaskToDisplayTypes(task: {
  [key: string]: unknown;
}): TimelineEvent {
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
    ? new Date(scheduledAt).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
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

  const durationMinutes =
    typeof task.duration_minutes === "number"
      ? task.duration_minutes
      : undefined;
  const goalName =
    typeof task.goal_name === "string" && task.goal_name
      ? task.goal_name
      : undefined;
  const isProjected = task.is_projected === true;
  const occurrenceDate =
    typeof task.occurrence_date === "string" ? task.occurrence_date : undefined;

  return {
    id,
    title,
    description,
    time,
    period,
    type: eventType,
    isPast,
    status,
    durationMinutes,
    goalName,
    isProjected,
    occurrenceDate,
  };
}

function getGreeting(name?: string): string {
  const hour = new Date().getHours();
  const salutation =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation;
}

function FlowPage() {
  const {
    events: initialEvents,
    user: loaderUser,
    selectedDate: loaderDate,
  } = Route.useLoaderData();
  const { complete_task_id, missed_task_id } = Route.useSearch();
  const { user } = useAuth();
  const [data, setData] = useState<{
    events: TimelineEvent[];
  }>({
    events: initialEvents,
  });

  const [isLoadingDate, setIsLoadingDate] = useState(false);

  // Keep local state in sync whenever the router loader provides fresh data.
  // Also clears the loading spinner set by handleDateChange.
  useEffect(() => {
    setData({ events: initialEvents });
    setIsLoadingDate(false);
  }, [initialEvents]);

  const displayName = user?.name ?? loaderUser.name;

  const handleDateChange = (date: string | null) => {
    setIsLoadingDate(true);
    navigate({
      to: "/",
      search: (prev) => ({ ...prev, date: date ?? undefined }),
    });
  };

  const handleComplete = useCallback(
    (taskId: string, occurrenceDate?: string) => {
      // Optimistic update — mark done immediately in local state.
      setData((prev) => ({
        events: prev.events.map((e) =>
          e.id === taskId ? { ...e, isPast: true } : e,
        ),
      }));

      tasksService.completeTask(taskId, occurrenceDate).catch((error) => {
        Sentry.captureException(error, { extra: { taskId } });
        // Revert optimistic update on error.
        setData((prev) => ({
          events: prev.events.map((e) =>
            e.id === taskId ? { ...e, isPast: false } : e,
          ),
        }));
      });
    },
    [],
  );

  const navigate = useNavigate();
  const [selectedTask, setSelectedTask] = useState<TimelineEvent | null>(null);

  const handleMissed = useCallback(
    (taskId: string, occurrenceDate?: string) => {
      setData((prev) => ({
        ...prev,
        events: prev.events.map((e) =>
          e.id === taskId ? { ...e, status: "missed", isPast: true } : e,
        ),
      }));
      tasksService
        .missedTask(taskId, occurrenceDate)
        .catch((error: unknown) => {
          Sentry.captureException(error, { extra: { taskId } });
        });
    },
    [],
  );

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
  }, [complete_task_id, handleComplete, handleMissed, missed_task_id]);

  // Derive the currently-displayed date from the loader (set on initial load / SSR)
  const [viewDate, setViewDate] = useState<string | null>(loaderDate ?? null);

  return (
    <div className="relative w-full h-screen flex flex-col overflow-hidden">
      <AmbientBackground />

      <DateHeader
        greeting={getGreeting(displayName)}
        selectedDate={viewDate}
        onDateChange={(d) => {
          setViewDate(d);
          handleDateChange(d);
        }}
      />

      {isLoadingDate ? (
        <div className="flex-1 flex items-center justify-center">
          <LoadingState />
        </div>
      ) : (
        <FlowTimeline
          events={data.events}
          onTaskClick={(event) => setSelectedTask(event)}
        />
      )}

      <BottomNav />

      <TaskDetailSheet
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
        onComplete={(taskId) => {
          handleComplete(taskId, selectedTask?.occurrenceDate);
          setSelectedTask(null);
        }}
        onMissed={(taskId) => {
          handleMissed(taskId, selectedTask?.occurrenceDate);
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

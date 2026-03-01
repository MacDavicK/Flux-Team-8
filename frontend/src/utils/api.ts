/**
 * Backend API base URL. Set VITE_API_URL in .env for production.
 */
const API_BASE =
  (typeof import.meta !== "undefined" &&
    (import.meta as ImportMeta & { env?: Record<string, string> }).env
      ?.VITE_API_URL) ||
  "http://localhost:8000";

export interface Task {
  id: string;
  title: string;
  start_time: string;
  end_time: string | null;
  state: string;
  description?: string;
  [key: string]: unknown;
}

export interface TimelineTasksResponse {
  tasks: Task[];
}

export interface Suggestion {
  new_start: string;
  new_end: string;
  label: string;
  rationale: string;
}

export interface SuggestResponse {
  event_id: string;
  task_title: string;
  suggestions: Suggestion[];
  skip_option: boolean;
  ai_message: string;
}

export async function fetchTimelineTasks(): Promise<Task[]> {
  const res = await fetch(`${API_BASE}/scheduler/tasks`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  const data = (await res.json()) as TimelineTasksResponse;
  return data.tasks ?? [];
}

export async function fetchSuggestions(
  eventId: string,
): Promise<SuggestResponse> {
  const res = await fetch(`${API_BASE}/scheduler/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId }),
  });
  if (!res.ok) {
    const err = (await res.json()).detail ?? res.statusText;
    throw new Error(err);
  }
  return res.json() as Promise<SuggestResponse>;
}

export async function applyReschedule(
  eventId: string,
  action: "reschedule" | "skip",
  newStart?: string,
  newEnd?: string,
): Promise<void> {
  const body: Record<string, string> = { event_id: eventId, action };
  if (action === "reschedule" && newStart && newEnd) {
    body.new_start = newStart;
    body.new_end = newEnd;
  }
  const res = await fetch(`${API_BASE}/scheduler/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = (await res.json()).detail ?? res.statusText;
    throw new Error(err);
  }
}

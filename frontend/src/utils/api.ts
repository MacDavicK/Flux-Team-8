/**
 * Flux API Client
 *
 * Thin fetch wrapper for backend communication.
 * Base URL is configurable via VITE_API_URL env var.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface RescheduleSuggestion {
  new_start: string; // ISO8601
  new_end: string; // ISO8601
  label: string; // e.g., "5:00 PM Today"
  rationale: string; // e.g., "Suggested 5 PM — it's your next free slot today."
}

export interface SchedulerSuggestResponse {
  event_id: string;
  task_title: string;
  suggestions: RescheduleSuggestion[];
  skip_option: boolean;
  ai_message: string;
}

export interface SchedulerApplyRequest {
  event_id: string;
  action: "reschedule" | "skip";
  new_start?: string;
  new_end?: string;
}

export interface SchedulerApplyResponse {
  event_id: string;
  action: string;
  new_state: string;
  new_start?: string;
  new_end?: string;
  message: string;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API ${res.status}: ${errorBody}`);
  }

  return res.json();
}

export async function fetchSuggestions(
  eventId: string,
): Promise<SchedulerSuggestResponse> {
  return apiRequest<SchedulerSuggestResponse>("/scheduler/suggest", {
    method: "POST",
    body: JSON.stringify({ event_id: eventId }),
  });
}

export async function applyReschedule(
  request: SchedulerApplyRequest,
): Promise<SchedulerApplyResponse> {
  return apiRequest<SchedulerApplyResponse>("/scheduler/apply", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

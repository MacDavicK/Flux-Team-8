/**
 * Single API client for Flux backend.
 * All requests use VITE_API_URL with /api/v1 prefix; auth from getInMemoryToken().
 */
import { getInMemoryToken } from "~/lib/apiClient";

const BASE_URL =
  (typeof import.meta !== "undefined" &&
    (import.meta as ImportMeta & { env?: Record<string, string> }).env
      ?.VITE_API_URL) ||
  "http://localhost:8000";

export interface Task {
  id: string;
  title: string;
  start_time?: string;
  end_time?: string | null;
  state: string;
  status?: string;
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

/** Alias for modal compatibility (SCRUM-33). */
export type RescheduleSuggestion = Suggestion;
/** Alias for modal compatibility (SCRUM-33). */
export type SchedulerSuggestResponse = SuggestResponse;

export interface ChatMessageResponse {
  conversation_id: string;
  message: string;
  agent_node?: string | null;
  proposed_plan?: { [key: string]: unknown } | null;
  requires_user_action: boolean;
}

class FluxAPI {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${BASE_URL}/api/v1${path}`;
    const token = this.token ?? getInMemoryToken();
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers as Record<string, string>),
      },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  }

  /** Backend may expose GET /health; if not, useBackendReady will fall back to mock. */
  health(): Promise<{ status: string }> {
    return fetch(`${BASE_URL}/health`)
      .then((r) =>
        r.ok ? r.json() : Promise.reject(new Error("Health check failed")),
      )
      .then((data) => data as { status: string });
  }

  chatMessage(
    message: string,
    conversationId?: string | null,
  ): Promise<ChatMessageResponse> {
    return this.request<ChatMessageResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
      }),
    });
  }

  chatHistory(
    conversationId?: string,
    limit = 50,
  ): Promise<{ messages: unknown[]; conversation_id: string | null }> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (conversationId) params.set("conversation_id", conversationId);
    return this.request(`/chat/history?${params}`);
  }

  chatConversations(limit = 20): Promise<{ conversations: unknown[] }> {
    return this.request(`/chat/conversations?limit=${limit}`);
  }

  /** Onboarding uses same POST /chat/message; optional convenience. */
  onboardingChat(message: string): Promise<ChatMessageResponse> {
    return this.chatMessage(message);
  }

  /** Onboarding status comes from /account/me; no dedicated endpoint. */
  onboardingStatus(): Promise<{ onboarded: boolean; current_step?: number }> {
    return this.request("/account/me");
  }

  todayTasks(): Promise<Task[]> {
    return this.request<Task[]>("/tasks/today");
  }

  completeTask(id: string): Promise<unknown> {
    return this.request(`/tasks/${id}/complete`, { method: "PATCH" });
  }

  missTask(id: string): Promise<unknown> {
    return this.request(`/tasks/${id}/missed`, { method: "PATCH" });
  }

  timelineTasks(): Promise<Task[]> {
    return this.request<TimelineTasksResponse>("/scheduler/tasks").then(
      (data) => data.tasks ?? [],
    );
  }

  schedulerSuggest(eventId: string): Promise<SuggestResponse> {
    return this.request<SuggestResponse>("/scheduler/suggest", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId }),
    });
  }

  schedulerApply(
    eventId: string,
    newStart?: string,
    newEnd?: string,
  ): Promise<unknown> {
    const action = newStart != null && newEnd != null ? "reschedule" : "skip";
    const body: Record<string, string> = { event_id: eventId, action };
    if (action === "reschedule" && newStart && newEnd) {
      body.new_start = newStart;
      body.new_end = newEnd;
    }
    return this.request("/scheduler/apply", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  analyticsOverview(): Promise<unknown> {
    return this.request("/analytics/overview");
  }

  analyticsWeekly(): Promise<unknown> {
    return this.request("/analytics/weekly");
  }

  analyticsGoals(): Promise<unknown> {
    return this.request("/analytics/goals");
  }

  analyticsMissedByCategory(): Promise<unknown> {
    return this.request("/analytics/missed-by-cat");
  }

  analyticsHeatmap(): Promise<unknown> {
    return this.request("/analytics/overview").then((data: unknown) =>
      typeof data === "object" && data !== null && "heatmap" in data
        ? (data as { heatmap: unknown }).heatmap
        : data,
    );
  }
}

export const api = new FluxAPI();

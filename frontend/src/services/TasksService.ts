import { apiFetch } from "~/lib/apiClient";

class TasksService {
  async getTasks(date?: string): Promise<{ [key: string]: unknown }[]> {
    const url = date
      ? `/api/v1/tasks?date=${encodeURIComponent(date)}`
      : "/api/v1/tasks";
    const response = await apiFetch(url);

    if (!response.ok) {
      throw new Error("Failed to fetch tasks");
    }

    return response.json();
  }

  async completeTask(
    taskId: string,
    occurrenceDate?: string,
  ): Promise<{ task_id: string; status: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/complete`, {
      method: "PATCH",
      ...(occurrenceDate
        ? { body: JSON.stringify({ occurrence_date: occurrenceDate }) }
        : {}),
    });

    if (!response.ok) {
      throw new Error("Failed to complete task");
    }

    return response.json();
  }

  async addTodo(
    title: string,
  ): Promise<{ task_id: string; title: string; status: string }> {
    const response = await apiFetch("/api/v1/tasks/todo", {
      method: "POST",
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error("Failed to add task");
    }

    return response.json();
  }

  async missedTask(
    taskId: string,
    occurrenceDate?: string,
  ): Promise<{ task_id: string; status: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/missed`, {
      method: "PATCH",
      ...(occurrenceDate
        ? { body: JSON.stringify({ occurrence_date: occurrenceDate }) }
        : {}),
    });

    if (!response.ok) {
      throw new Error("Failed to mark task as missed");
    }

    return response.json();
  }

  async confirmReschedule(
    taskId: string,
    scheduledAt: string,
    scope: string = "one",
    occurrenceDate?: string,
  ): Promise<{
    original_task_id: string;
    new_task_id: string;
    status: string;
    scheduled_at: string;
    updated_count?: number;
  }> {
    const response = await apiFetch(
      `/api/v1/tasks/${taskId}/reschedule-confirm`,
      {
        method: "PATCH",
        body: JSON.stringify({
          scheduled_at: scheduledAt,
          scope,
          ...(occurrenceDate ? { occurrence_date: occurrenceDate } : {}),
        }),
      },
    );
    if (!response.ok) throw new Error("Failed to confirm reschedule");
    return response.json();
  }
}

export const tasksService = new TasksService();

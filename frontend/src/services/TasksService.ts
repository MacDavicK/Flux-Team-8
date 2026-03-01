import { apiFetch } from "~/lib/apiClient";
import type { ChatMessageResponse, RescheduleRequest } from "~/types";

class TasksService {
  async getTodayTasks(): Promise<{ [key: string]: unknown }[]> {
    const response = await apiFetch("/api/v1/tasks/today");

    if (!response.ok) {
      throw new Error("Failed to fetch today's tasks");
    }

    return response.json();
  }

  async completeTask(
    taskId: string,
  ): Promise<{ task_id: string; status: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/complete`, {
      method: "PATCH",
    });

    if (!response.ok) {
      throw new Error("Failed to complete task");
    }

    return response.json();
  }

  async rescheduleTask(
    taskId: string,
    data: RescheduleRequest,
  ): Promise<ChatMessageResponse> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/reschedule`, {
      method: "POST",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error("Failed to reschedule task");
    }

    return response.json();
  }
}

export const tasksService = new TasksService();

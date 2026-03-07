import { apiFetch } from "~/lib/apiClient";

class TasksService {
  async getTodayTasks(): Promise<{ [key: string]: unknown }[]> {
    const response = await apiFetch("/api/v1/tasks/today");

    if (!response.ok) {
      throw new Error("Failed to fetch today's tasks");
    }

    return response.json();
  }

  async completeTask(taskId: string): Promise<{ task_id: string; status: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/complete`, {
      method: "PATCH",
    });

    if (!response.ok) {
      throw new Error("Failed to complete task");
    }

    return response.json();
  }

  async addTodo(title: string): Promise<{ task_id: string; title: string; status: string }> {
    const response = await apiFetch("/api/v1/tasks/todo", {
      method: "POST",
      body: JSON.stringify({ title }),
    });

    if (!response.ok) {
      throw new Error("Failed to add task");
    }

    return response.json();
  }

  async missedTask(taskId: string): Promise<{ task_id: string; status: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/missed`, {
      method: "PATCH",
    });

    if (!response.ok) {
      throw new Error("Failed to mark task as missed");
    }

    return response.json();
  }

  async confirmReschedule(taskId: string, scheduledAt: string): Promise<{ original_task_id: string; new_task_id: string; status: string; scheduled_at: string }> {
    const response = await apiFetch(`/api/v1/tasks/${taskId}/reschedule-confirm`, {
      method: "PATCH",
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    });
    if (!response.ok) throw new Error("Failed to confirm reschedule");
    return response.json();
  }


}

export const tasksService = new TasksService();

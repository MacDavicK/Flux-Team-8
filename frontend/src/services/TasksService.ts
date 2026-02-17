import type { TasksResponse } from "~/mocks/tasksHandlers";

class TasksService {
  async getTasks(): Promise<TasksResponse> {
    const response = await fetch("/api/tasks");

    if (!response.ok) {
      throw new Error("Failed to fetch tasks");
    }

    return response.json();
  }
}

export const tasksService = new TasksService();

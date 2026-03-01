import { apiFetch } from "~/lib/apiClient";

class DemoService {
  async triggerLocation(): Promise<{ [key: string]: unknown }> {
    const response = await apiFetch("/api/v1/demo/trigger-location", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Failed to trigger location demo");
    }

    return response.json();
  }
}

export const demoService = new DemoService();

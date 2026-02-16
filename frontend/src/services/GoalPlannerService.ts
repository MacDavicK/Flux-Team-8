import type { AgentResponse } from "~/types/notification";

export type { GoalContext, PlanMilestone } from "~/types/goal";
export type { AgentResponse };
export { AgentState } from "~/types/goal";

class GoalPlannerService {
  async sendMessage(
    message: string,
    state: string,
    context: any,
  ): Promise<{
    response: AgentResponse;
    newState: string;
    newContext: any;
  }> {
    const response = await fetch("/api/goal-planner/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, state, context }),
    });

    if (!response.ok) {
      throw new Error("Failed to send message to Goal Planner Service");
    }

    return response.json();
  }

  async triggerSimulation(
    trigger: string,
    task?: string,
  ): Promise<AgentResponse> {
    const response = await fetch("/api/simulation/trigger", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ trigger, task }),
    });

    if (!response.ok) {
      throw new Error("Failed to trigger simulation");
    }

    const data = await response.json();
    return data.response;
  }
}

export const goalPlannerService = new GoalPlannerService();

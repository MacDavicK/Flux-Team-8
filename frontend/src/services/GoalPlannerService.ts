export type GoalContext = {
  goal?: string;
  timeline?: string;
  currentWeight?: string;
  targetWeight?: string;
  preferences?: string;
};

export type PlanMilestone = {
  week: string;
  milestone: string;
  tasks: string[];
};

export type AgentResponse = {
  message: string;
  type: "text" | "plan";
  plan?: PlanMilestone[];
  suggestedAction?: string;
};

export enum AgentState {
  IDLE = "IDLE",
  GATHERING_TIMELINE = "GATHERING_TIMELINE",
  GATHERING_CURRENT_WEIGHT = "GATHERING_CURRENT_WEIGHT",
  GATHERING_TARGET_WEIGHT = "GATHERING_TARGET_WEIGHT",
  GATHERING_PREFERENCES = "GATHERING_PREFERENCES",
  PLAN_READY = "PLAN_READY",
  CONFIRMED = "CONFIRMED",
}

class GoalPlannerService {
  async sendMessage(
    message: string,
    state: AgentState,
    context: GoalContext,
  ): Promise<{
    response: AgentResponse;
    newState: AgentState;
    newContext: GoalContext;
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
}

export const goalPlannerService = new GoalPlannerService();

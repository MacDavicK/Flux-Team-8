export type GoalContext = {
  goal?: string;
  timeline?: string;
  currentWeight?: string;
  targetWeight?: string;
  preferences?: string;
};

export type PlanTask = {
  title: string;
  duration?: string;
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

export class GoalPlannerAgent {
  private state: AgentState = AgentState.IDLE;
  private context: GoalContext = {};

  async processMessage(message: string): Promise<AgentResponse> {
    const input = message.toLowerCase();

    switch (this.state) {
      case AgentState.IDLE:
        if (input.includes("lose weight") || input.includes("wedding")) {
          this.context.goal = message;
          this.state = AgentState.GATHERING_TIMELINE;
          return {
            message: "That's a great goal! 💪 When is the wedding?",
            type: "text",
          };
        }
        return {
          message:
            "Hi! I'm here to help you break down your goals into manageable tasks. What would you like to achieve?",
          type: "text",
        };

      case AgentState.GATHERING_TIMELINE:
        this.context.timeline = message;
        this.state = AgentState.GATHERING_CURRENT_WEIGHT;
        return {
          message:
            "Perfect! That gives us some time. What do you weigh now, if you don't mind sharing?",
          type: "text",
        };

      case AgentState.GATHERING_CURRENT_WEIGHT:
        this.context.currentWeight = message;
        this.state = AgentState.GATHERING_TARGET_WEIGHT;
        return {
          message:
            "And what's your target? Or should I suggest a healthy goal?",
          type: "text",
          suggestedAction: "Suggest a goal",
        };

      case AgentState.GATHERING_TARGET_WEIGHT:
        if (input.includes("suggest")) {
          this.context.targetWeight = "75 kg"; // Smart default
        } else {
          this.context.targetWeight = message;
        }
        this.state = AgentState.GATHERING_PREFERENCES;
        return {
          message: "Do you prefer gym, home workouts, or mostly diet changes?",
          type: "text",
        };

      case AgentState.GATHERING_PREFERENCES:
        this.context.preferences = message;
        this.state = AgentState.PLAN_READY;
        return {
          message:
            "I've put together a 6-week plan for you based on our conversation. Here's how we'll reach your goal!",
          type: "plan",
          plan: [
            {
              week: "1",
              milestone: "Baseline & Habits",
              tasks: ["3x gym sessions", "log meals daily", "weigh-in Sunday"],
            },
            {
              week: "2-3",
              milestone: "Build Consistency",
              tasks: ["4x gym sessions", "meal prep Sundays"],
            },
            {
              week: "4-5",
              milestone: "Intensify",
              tasks: ["Add cardio", "reduce portions"],
            },
            {
              week: "6",
              milestone: "Final Push",
              tasks: ["Daily activity", "wedding prep focus"],
            },
          ],
        };

      case AgentState.PLAN_READY:
        if (
          input.includes("yes") ||
          input.includes("good") ||
          input.includes("start")
        ) {
          this.state = AgentState.CONFIRMED;
          return {
            message:
              "✅ Plan activated! Your tasks have been scheduled. I'll remind you about your workouts and check in weekly on your progress. Sound good?",
            type: "text",
          };
        }
        return {
          message: "Would you like me to adjust anything in the plan?",
          type: "text",
        };

      case AgentState.CONFIRMED:
        return {
          message:
            "You're all set! Let's crush those goals. Anything else you need help with?",
          type: "text",
        };

      default:
        return {
          message:
            "I'm not sure how to handle that right now. Should we start over?",
          type: "text",
        };
    }
  }

  reset() {
    this.state = AgentState.IDLE;
    this.context = {};
  }
}

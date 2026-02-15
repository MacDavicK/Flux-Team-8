import { delay, HttpResponse, http } from "msw";

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

export const handlers = [
  http.post("/api/goal-planner/message", async ({ request }) => {
    const { message, state, context } = (await request.json()) as {
      message: string;
      state: AgentState;
      context: GoalContext;
    };

    // Simulate API delay
    await delay(500);

    const input = message.toLowerCase();
    let newState = state;
    const newContext = { ...context };
    let response: AgentResponse;

    switch (state) {
      case AgentState.IDLE:
        if (input.includes("lose weight") || input.includes("wedding")) {
          newContext.goal = message;
          newState = AgentState.GATHERING_TIMELINE;
          response = {
            message: "That's a great goal! 💪 When is the wedding?",
            type: "text",
          };
        } else {
          response = {
            message:
              "Hi! I'm here to help you break down your goals into manageable tasks. What would you like to achieve?",
            type: "text",
          };
        }
        break;

      case AgentState.GATHERING_TIMELINE:
        newContext.timeline = message;
        newState = AgentState.GATHERING_CURRENT_WEIGHT;
        response = {
          message:
            "Perfect! That gives us some time. What do you weigh now, if you don't mind sharing?",
          type: "text",
        };
        break;

      case AgentState.GATHERING_CURRENT_WEIGHT:
        newContext.currentWeight = message;
        newState = AgentState.GATHERING_TARGET_WEIGHT;
        response = {
          message:
            "And what's your target? Or should I suggest a healthy goal?",
          type: "text",
          suggestedAction: "Suggest a goal",
        };
        break;

      case AgentState.GATHERING_TARGET_WEIGHT:
        if (input.includes("suggest")) {
          newContext.targetWeight = "75 kg"; // Smart default
        } else {
          newContext.targetWeight = message;
        }
        newState = AgentState.GATHERING_PREFERENCES;
        response = {
          message: "Do you prefer gym, home workouts, or mostly diet changes?",
          type: "text",
        };
        break;

      case AgentState.GATHERING_PREFERENCES:
        newContext.preferences = message;
        newState = AgentState.PLAN_READY;
        response = {
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
        break;

      case AgentState.PLAN_READY:
        if (
          input.includes("yes") ||
          input.includes("good") ||
          input.includes("start")
        ) {
          newState = AgentState.CONFIRMED;
          response = {
            message:
              "✅ Plan activated! Your tasks have been scheduled. I'll remind you about your workouts and check in weekly on your progress. Sound good?",
            type: "text",
          };
        } else {
          response = {
            message: "Would you like me to adjust anything in the plan?",
            type: "text",
          };
        }
        break;

      case AgentState.CONFIRMED:
        response = {
          message:
            "You're all set! Let's crush those goals. Anything else you need help with?",
          type: "text",
        };
        break;

      default:
        response = {
          message:
            "I'm not sure how to handle that right now. Should we start over?",
          type: "text",
        };
    }

    return HttpResponse.json({ response, newState, newContext });
  }),
];

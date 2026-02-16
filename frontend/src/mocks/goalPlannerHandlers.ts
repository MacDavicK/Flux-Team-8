import { delay, HttpResponse, http } from "msw";
import { AgentState } from "~/types/goal";
import {
  LocationReminderState,
  NotificationTrigger,
} from "~/types/notification";

async function handleGoalPlannerMessage(request: Request) {
  const { message, state, context } = (await request.json()) as {
    message: string;
    state: string;
    context: any;
  };

  await delay(500);

  const input = message.toLowerCase();
  let newState = state;
  const newContext = { ...context };
  let response: any;

  // Decide which scenario we are in
  const isLocationScenario =
    input.includes("remind") ||
    Object.values(LocationReminderState).includes(
      state as LocationReminderState,
    );

  if (isLocationScenario && state === AgentState.IDLE) {
    if (
      input.includes("remind me to") &&
      (input.includes("pick up") || input.includes("buy"))
    ) {
      newContext.locationTask = message.replace(/remind me to/i, "").trim();
      newState = LocationReminderState.WAITING_FOR_TRIGGER;

      response = {
        message: "Got it! I'll remind you when you're out near a store. 📍",
        type: "text",
        trigger: NotificationTrigger.NEAR_GROCERY,
      };
      return HttpResponse.json({ response, newState, newContext });
    }
  }

  // Handle Location Reminder States
  if (
    state === LocationReminderState.NEAR_STORE ||
    state === LocationReminderState.WAITING_FOR_TRIGGER
  ) {
    if (
      input.includes("done") ||
      input.includes("ok") ||
      input.includes("thanks")
    ) {
      newState = LocationReminderState.COMPLETED;
      response = {
        message: "✅ Great! I've marked that as complete.",
        type: "text",
      };
    } else if (input.includes("snooze")) {
      newState = LocationReminderState.SNOOZED;
      response = {
        message: "No problem! When should I remind you again?",
        type: "text",
      };
    } else if (state === LocationReminderState.WAITING_FOR_TRIGGER) {
      // Fallback if it's not a direct command but we are in waiting state
      // We might want to let the goal planner handle it if it doesn't look like location stuff
      // but for now, let's keep it simple.
    }

    if (response) {
      return HttpResponse.json({ response, newState, newContext });
    }
  }

  if (state === LocationReminderState.SNOOZED) {
    newState = LocationReminderState.WAITING_FOR_TRIGGER;
    response = {
      message:
        "Understood. I'll keep an eye on your location and remind you later.",
      type: "text",
    };
    return HttpResponse.json({ response, newState, newContext });
  }

  // Handle Goal Planner States
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
        message: "And what's your target? Or should I suggest a healthy goal?",
        type: "text",
        suggestedAction: "Suggest a goal",
      };
      break;

    case AgentState.GATHERING_TARGET_WEIGHT:
      if (input.includes("suggest")) {
        newContext.targetWeight = "75 kg";
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
}

async function handleSimulationTrigger(request: Request) {
  const { trigger, task } = (await request.json()) as {
    trigger: string;
    task?: string;
  };

  await delay(500);

  let response: any;

  if (trigger === "leaving_home") {
    response = {
      message:
        "You're out! Want to pick up " +
        (task || "tomatoes") +
        " now? 🍅\nClosest grocery: 0.3 mi",
      type: "notification",
      distance: "0.3 mi",
    };
  } else if (trigger === "near_grocery") {
    response = {
      message:
        "You're near a grocery store! Want to pick up " +
        (task || "tomatoes") +
        " now? 🍅\nDistance: 0.1 mi",
      type: "notification",
      distance: "0.1 mi",
    };
  } else if (trigger === "whatsapp") {
    response = {
      message: `Hey! Don't forget the ${task || "tomatoes"} 🍅`,
      type: "whatsapp",
    };
  } else if (trigger === "call") {
    response = {
      message:
        "Quick voice reminder: Don't forget to pick up the " +
        (task || "tomatoes") +
        ". Would you like to snooze this?",
      type: "call",
    };
  }

  return HttpResponse.json({ response });
}

export const goalPlannerHandlers = [
  http.post("/api/goal-planner/message", async ({ request }) => {
    return handleGoalPlannerMessage(request);
  }),
  http.post("/api/simulation/trigger", async ({ request }) => {
    return handleSimulationTrigger(request);
  }),
];

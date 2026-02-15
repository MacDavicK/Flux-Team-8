export enum LocationReminderState {
  IDLE = "IDLE",
  WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER",
  NEAR_STORE = "NEAR_STORE",
  SNOOZED = "SNOOZED",
  COMPLETED = "COMPLETED",
}

export type AgentResponse = {
  message: string;
  type: "text" | "plan" | "notification" | "whatsapp" | "call";
  distance?: string;
  trigger?: "leaving_home" | "near_grocery";
  plan?: unknown[];
  suggestedAction?: string;
};

export class LocationReminderAgent {
  private state: LocationReminderState = LocationReminderState.IDLE;
  private task: string | null = null;

  async processMessage(message: string): Promise<AgentResponse | null> {
    const input = message.toLowerCase();

    if (this.state === LocationReminderState.IDLE) {
      if (
        input.includes("remind me to") &&
        (input.includes("pick up") || input.includes("buy"))
      ) {
        this.task = message.replace(/remind me to/i, "").trim();
        this.state = LocationReminderState.WAITING_FOR_TRIGGER;

        return {
          message: "Got it! I'll remind you when you're out near a store. 📍",
          type: "text",
          trigger: "near_grocery",
        };
      }
    }

    if (
      this.state === LocationReminderState.NEAR_STORE ||
      this.state === LocationReminderState.WAITING_FOR_TRIGGER
    ) {
      if (
        input.includes("done") ||
        input.includes("ok") ||
        input.includes("thanks")
      ) {
        this.state = LocationReminderState.COMPLETED;
        return {
          message: "✅ Great! I've marked that as complete.",
          type: "text",
        };
      }
      if (input.includes("snooze")) {
        this.state = LocationReminderState.SNOOZED;
        return {
          message: "No problem! When should I remind you again?",
          type: "text",
        };
      }
    }

    if (this.state === LocationReminderState.SNOOZED) {
      this.state = LocationReminderState.WAITING_FOR_TRIGGER;
      return {
        message:
          "Understood. I'll keep an eye on your location and remind you later.",
        type: "text",
      };
    }

    return null;
  }

  simulateTrigger(trigger: "leaving_home" | "near_grocery"): AgentResponse {
    if (trigger === "leaving_home") {
      return {
        message:
          "You're out! Want to pick up " +
          (this.task || "tomatoes") +
          " now? 🍅\nClosest grocery: 0.3 mi",
        type: "notification",
        distance: "0.3 mi",
      };
    }

    return {
      message:
        "You're near a grocery store! Want to pick up " +
        (this.task || "tomatoes") +
        " now? 🍅\nDistance: 0.1 mi",
      type: "notification",
      distance: "0.1 mi",
    };
  }

  simulateEscalation(level: "whatsapp" | "call"): AgentResponse {
    if (level === "whatsapp") {
      return {
        message: `Hey! Don't forget the ${this.task || "tomatoes"} 🍅`,
        type: "whatsapp",
      };
    }

    return {
      message:
        "Quick voice reminder: Don't forget to pick up the " +
        (this.task || "tomatoes") +
        ". Would you like to snooze this?",
      type: "call",
    };
  }

  getState() {
    return this.state;
  }

  reset() {
    this.state = LocationReminderState.IDLE;
    this.task = null;
  }
}

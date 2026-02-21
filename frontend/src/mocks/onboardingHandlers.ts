import { delay, HttpResponse, http } from "msw";
import type {
  OnboardingChatResponse,
  OnboardingProfile,
  OnboardingStatusResponse,
  OnboardingStep,
} from "~/types";

let onboardingProfile: Partial<OnboardingProfile> = {};
let currentStep: OnboardingStep = "name";
let isOnboarded = false;

const ONBOARDING_QUESTIONS: Record<OnboardingStep, string> = {
  name: "Welcome to Flux! What should I call you?",
  wake_time: "Nice to meet you, {name}! What time do you usually wake up?",
  sleep_time: "And what time do you go to bed?",
  work_schedule:
    "Do you work during the day? If so, roughly what hours? (e.g., 9am-5pm)",
  chronotype: "Are you a morning person or a night owl?",
  locations:
    "Let's set up your locations. What's your home address or area? And your work location?",
  existing_commitments:
    "Do you have any existing regular commitments? (e.g., gym on Tuesday evenings, weekly meetings)",
  first_goal: "Great! Now, what's the first thing you'd like to work on?",
  complete: "You're all set! Let's get started.",
};

const parseTime = (input: string): string | undefined => {
  const timeMatch = input.match(/(\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)?/);
  if (timeMatch) {
    const hours = Number.parseInt(timeMatch[1], 10);
    const minutes = timeMatch[2] ? Number.parseInt(timeMatch[2], 10) : 0;
    const period = timeMatch[3]?.toLowerCase();

    let hour = hours;
    if (period === "pm" && hour < 12) hour += 12;
    if (period === "am" && hour === 12) hour = 0;

    return `${hour.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}`;
  }
  return undefined;
};

const parseWorkHours = (
  input: string,
): { start: string; end: string } | undefined => {
  const match = input.match(
    /(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*[-–to]+\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?/i,
  );
  if (match) {
    const startPeriod = match[3]?.toLowerCase();
    const endPeriod = match[6]?.toLowerCase();

    let startHour = Number.parseInt(match[1], 10);
    let endHour = Number.parseInt(match[4], 10);

    if (startPeriod === "pm" && startHour < 12) startHour += 12;
    if (startPeriod === "am" && startHour === 12) startHour = 0;
    if (endPeriod === "pm" && endHour < 12) endHour += 12;
    if (endPeriod === "am" && endHour === 12) endHour = 0;

    const startMin = match[2] || "00";
    const endMin = match[5] || "00";

    return {
      start: `${startHour.toString().padStart(2, "0")}:${startMin}`,
      end: `${endHour.toString().padStart(2, "0")}:${endMin}`,
    };
  }
  return undefined;
};

const parseChronotype = (input: string): "morning" | "evening" | "neutral" => {
  const lower = input.toLowerCase();
  if (
    lower.includes("morning") ||
    lower.includes("early") ||
    lower.includes("lark")
  ) {
    return "morning";
  }
  if (
    lower.includes("night") ||
    lower.includes("evening") ||
    lower.includes("owl")
  ) {
    return "evening";
  }
  return "neutral";
};

const parseCommitments = (
  input: string,
): Array<{
  title: string;
  days: string[];
  time: string;
  duration_minutes: number;
}> => {
  const commitments: Array<{
    title: string;
    days: string[];
    time: string;
    duration_minutes: number;
  }> = [];

  const commitmentPatterns = [
    /(\w+)\s+(?:on\s+)?(\w+day)\s*(?:evenings?|mornings?)?\s*(?:at\s+)?(\d{1,2}):?(\d{2})?\s*(am|pm)?/gi,
    /(?:go to|attend|have)\s+(\w+)\s+(?:on\s+)?(\w+day)/gi,
  ];

  for (const pattern of commitmentPatterns) {
    let match: RegExpExecArray | null = null;
    match = pattern.exec(input);
    while (match !== null) {
      const title = match[1];
      const day = match[2];
      const time = match[3] && match[4] ? `${match[3]}:${match[4]}` : "19:00";

      commitments.push({
        title: title.charAt(0).toUpperCase() + title.slice(1),
        days: [day.charAt(0).toUpperCase() + day.slice(1)],
        time: time,
        duration_minutes: 60,
      });
      match = pattern.exec(input);
    }
  }

  if (
    commitments.length === 0 &&
    input.toLowerCase() !== "no" &&
    input.toLowerCase() !== "none"
  ) {
    commitments.push({
      title: input.substring(0, 50),
      days: ["Monday"],
      time: "19:00",
      duration_minutes: 60,
    });
  }

  return commitments;
};

const getNextStep = (current: OnboardingStep): OnboardingStep => {
  const steps: OnboardingStep[] = [
    "name",
    "wake_time",
    "sleep_time",
    "work_schedule",
    "chronotype",
    "locations",
    "existing_commitments",
    "first_goal",
    "complete",
  ];
  const currentIndex = steps.indexOf(current);
  return steps[currentIndex + 1] || "complete";
};

const processMessage = (
  message: string,
  currentProfile: Partial<OnboardingProfile>,
  step: OnboardingStep,
): { profile: Partial<OnboardingProfile>; nextStep: OnboardingStep } => {
  const profile = { ...currentProfile };
  let nextStep: OnboardingStep = getNextStep(step);

  switch (step) {
    case "name":
      profile.name = message.trim();
      break;
    case "wake_time": {
      const wakeTime = parseTime(message);
      if (wakeTime) {
        profile.sleep_window = {
          start: profile.sleep_window?.start || "23:00",
          end: wakeTime,
        };
      }
      break;
    }
    case "sleep_time": {
      const sleepTime = parseTime(message);
      if (sleepTime) {
        profile.sleep_window = {
          ...profile.sleep_window,
          start: sleepTime,
          end: profile.sleep_window?.end || "07:00",
        };
      }
      break;
    }
    case "work_schedule": {
      if (message.toLowerCase() !== "no" && message.toLowerCase() !== "none") {
        const hours = parseWorkHours(message);
        if (hours) {
          profile.work_hours = {
            start: hours.start,
            end: hours.end,
            days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
          };
        }
      }
      break;
    }
    case "chronotype":
      profile.chronotype = parseChronotype(message);
      break;
    case "locations": {
      const parts = message.split(/[,&]|\band\b/i).map((p) => p.trim());
      profile.locations = {
        home: parts[0] || "Home",
        work: parts[1] || "Work",
      };
      break;
    }
    case "existing_commitments": {
      const commitments = parseCommitments(message);
      profile.existing_commitments = commitments;
      break;
    }
    case "first_goal":
      break;
    case "complete":
      nextStep = "complete";
      break;
  }

  return { profile, nextStep };
};

export const onboardingHandlers = [
  http.get("/api/onboarding/status", async () => {
    await delay(200);

    return HttpResponse.json({
      onboarded: isOnboarded,
      onboardingProfile: isOnboarded ? onboardingProfile : undefined,
    } as OnboardingStatusResponse);
  }),

  http.post("/api/onboarding/chat", async ({ request }) => {
    await delay(400);

    const body = (await request.json()) as {
      message: string;
      currentProfile: Partial<OnboardingProfile>;
    };

    const { message, currentProfile } = body;
    const { profile, nextStep } = processMessage(
      message,
      currentProfile,
      currentStep,
    );

    onboardingProfile = profile;
    currentStep = nextStep;

    let responseMessage = ONBOARDING_QUESTIONS[nextStep] || "Let's continue...";

    if (nextStep === "wake_time" && profile.name) {
      responseMessage = responseMessage.replace("{name}", profile.name);
    }

    if (nextStep === "complete") {
      responseMessage = "You're all set! Let's get started on your goals.";
    }

    return HttpResponse.json({
      message: responseMessage,
      nextStep,
      profile,
      isComplete: nextStep === "complete",
    } as OnboardingChatResponse);
  }),

  http.post("/api/onboarding/complete", async ({ request }) => {
    await delay(300);

    const profile = (await request.json()) as OnboardingProfile;
    onboardingProfile = profile;
    isOnboarded = true;

    return HttpResponse.json({ success: true });
  }),

  http.post("/api/onboarding/reset", async () => {
    await delay(200);
    onboardingProfile = {};
    currentStep = "name";
    isOnboarded = false;

    return HttpResponse.json({ success: true });
  }),
];

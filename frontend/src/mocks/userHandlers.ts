import { delay, HttpResponse, http } from "msw";
import type {
  UserEnergyAuraResponse,
  UserFocusDistributionResponse,
  UserProfileResponse,
  UserStatsResponse,
  UserWeeklyInsightResponse,
} from "~/types";

const userProfile: UserProfileResponse = {
  id: "user-1",
  name: "Harshal",
  email: "harshal@example.com",
  avatar: undefined,
};

const userStats: UserStatsResponse = {
  title: "This Week",
  stats: [
    { icon: "check", value: "24", label: "Done" },
    { icon: "clock", value: "12h", label: "Focus" },
    { icon: "flame", value: "7", label: "Streak" },
  ],
};

const generateEnergyData = () => {
  return Array.from({ length: 50 }, (_, i) => ({
    date: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
    intensity: Math.random(),
  }));
};

const userEnergyAura: UserEnergyAuraResponse = {
  data: generateEnergyData(),
};

const userFocusDistribution: UserFocusDistributionResponse = {
  work: 45,
  personal: 30,
  health: 25,
};

const userWeeklyInsight: UserWeeklyInsightResponse = {
  title: "This Week's Insight",
  insight:
    "Your peak productivity happens on Tuesday mornings. Consider scheduling your most important tasks during this time window for optimal focus and energy.",
};

export const userHandlers = [
  http.get("/api/user/profile", async () => {
    await delay(300);
    return HttpResponse.json(userProfile);
  }),

  http.get("/api/user/stats", async () => {
    await delay(400);
    return HttpResponse.json(userStats);
  }),

  http.get("/api/user/energy-aura", async () => {
    await delay(500);
    return HttpResponse.json(userEnergyAura);
  }),

  http.get("/api/user/focus-distribution", async () => {
    await delay(450);
    return HttpResponse.json(userFocusDistribution);
  }),

  http.get("/api/user/weekly-insight", async () => {
    await delay(350);
    return HttpResponse.json(userWeeklyInsight);
  }),
];

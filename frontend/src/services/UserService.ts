import type {
  UserEnergyAuraResponse,
  UserFocusDistributionResponse,
  UserProfileResponse,
  UserStatsResponse,
  UserWeeklyInsightResponse,
} from "~/types";

class UserService {
  async getProfile(): Promise<UserProfileResponse> {
    const response = await fetch("/api/user/profile");

    if (!response.ok) {
      throw new Error("Failed to fetch user profile");
    }

    return response.json();
  }

  async getStats(): Promise<UserStatsResponse> {
    const response = await fetch("/api/user/stats");

    if (!response.ok) {
      throw new Error("Failed to fetch user stats");
    }

    return response.json();
  }

  async getEnergyAura(): Promise<UserEnergyAuraResponse> {
    const response = await fetch("/api/user/energy-aura");

    if (!response.ok) {
      throw new Error("Failed to fetch energy aura data");
    }

    return response.json();
  }

  async getFocusDistribution(): Promise<UserFocusDistributionResponse> {
    const response = await fetch("/api/user/focus-distribution");

    if (!response.ok) {
      throw new Error("Failed to fetch focus distribution data");
    }

    return response.json();
  }

  async getWeeklyInsight(): Promise<UserWeeklyInsightResponse> {
    const response = await fetch("/api/user/weekly-insight");

    if (!response.ok) {
      throw new Error("Failed to fetch weekly insight");
    }

    return response.json();
  }
}

export const userService = new UserService();

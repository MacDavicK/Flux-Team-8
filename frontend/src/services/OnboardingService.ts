import type {
  OnboardingChatResponse,
  OnboardingProfile,
  OnboardingStatusResponse,
} from "~/types";

class OnboardingService {
  async getStatus(): Promise<OnboardingStatusResponse> {
    const response = await fetch("/api/onboarding/status");

    if (!response.ok) {
      throw new Error("Failed to fetch onboarding status");
    }

    return response.json();
  }

  async sendMessage(
    message: string,
    currentProfile: Partial<OnboardingProfile>,
  ): Promise<OnboardingChatResponse> {
    const response = await fetch("/api/onboarding/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        currentProfile,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to process message");
    }

    return response.json();
  }

  async complete(profile: OnboardingProfile): Promise<void> {
    const response = await fetch("/api/onboarding/complete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      throw new Error("Failed to complete onboarding");
    }
  }
}

export const onboardingService = new OnboardingService();

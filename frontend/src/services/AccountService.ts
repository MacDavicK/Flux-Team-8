import { apiFetch } from "~/lib/apiClient";
import type { AccountMe, AccountPatchRequest } from "~/types";

class AccountService {
  async getMe(): Promise<AccountMe> {
    const response = await apiFetch("/api/v1/account/me");

    if (!response.ok) {
      throw new Error("Failed to fetch account");
    }

    return response.json();
  }

  async patchMe(data: AccountPatchRequest): Promise<AccountMe> {
    const response = await apiFetch("/api/v1/account/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error("Failed to update account");
    }

    return response.json();
  }

  async getOverview(): Promise<{ [key: string]: unknown }> {
    const response = await apiFetch("/api/v1/analytics/overview");

    if (!response.ok) {
      throw new Error("Failed to fetch analytics overview");
    }

    return response.json();
  }

  async getWeeklyStats(weeks?: number): Promise<unknown[]> {
    const url =
      weeks != null
        ? `/api/v1/analytics/weekly?weeks=${weeks}`
        : "/api/v1/analytics/weekly";
    const response = await apiFetch(url);

    if (!response.ok) {
      throw new Error("Failed to fetch weekly stats");
    }

    return response.json();
  }

  async getMissedByCategory(): Promise<unknown[]> {
    const response = await apiFetch("/api/v1/analytics/missed-by-cat");

    if (!response.ok) {
      throw new Error("Failed to fetch missed-by-category data");
    }

    return response.json();
  }
}

export const accountService = new AccountService();

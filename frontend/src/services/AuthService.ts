import type {
  AuthStatusResponse,
  LoginRequest,
  LoginResponse,
  SignupRequest,
  SignupResponse,
  User,
} from "~/types";
import { isClient } from "~/utils/env";

const AUTH_COOKIE_NAME = "flux_auth_token";

class AuthService {
  private getCookie(name: string): string | undefined {
    if (!isClient()) return undefined;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(";").shift();
    }
    return undefined;
  }

  private deleteCookie(name: string): void {
    if (!isClient()) return;
    // biome-ignore lint/suspicious/noDocumentCookie: Intentional cookie deletion for logout
    document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }

  isAuthenticated(): boolean {
    return !!this.getCookie(AUTH_COOKIE_NAME);
  }

  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result: LoginResponse = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.message || "Failed to login");
    }

    return result;
  }

  async signup(data: SignupRequest): Promise<SignupResponse> {
    const response = await fetch("/api/auth/signup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result: SignupResponse = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.message || "Failed to create account");
    }

    return result;
  }

  async logout(): Promise<void> {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
      });
    } finally {
      this.deleteCookie(AUTH_COOKIE_NAME);
    }
  }

  async getAuthStatus(): Promise<AuthStatusResponse> {
    const response = await fetch("/api/auth/status");

    if (!response.ok) {
      return { isAuthenticated: false };
    }

    return response.json();
  }

  async getCurrentUser(): Promise<User | undefined> {
    const status = await this.getAuthStatus();
    return status.user;
  }
}

export const authService = new AuthService();

import {
  serverGetGoogleOAuthUrl,
  serverLogin,
  serverLogout,
  serverSignup,
} from "~/lib/authServerFns";
import type { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from "~/types";

// AuthService is now a thin wrapper around server functions.
// No Supabase SDK is imported here. No localStorage is touched.
// Session tokens are managed server-side via httpOnly cookies.
// AuthContext owns the in-memory token lifecycle (see AuthContext.tsx).

class AuthService {
  async login(data: LoginRequest): Promise<LoginResponse> {
    const result = await serverLogin({ data });
    return {
      success: true,
      user: { ...result.user, onboarded: false },
    };
  }

  async signup(data: SignupRequest): Promise<SignupResponse> {
    const result = await serverSignup({ data });
    return {
      success: true,
      user: { ...result.user, onboarded: false },
    };
  }

  /**
   * Initiates the Google OAuth flow.
   * The OAuth redirect URL is generated server-side (keys hidden from client).
   * The browser is then navigated to Google's consent screen.
   */
  async loginWithGoogle(): Promise<void> {
    const { url } = await serverGetGoogleOAuthUrl();
    window.location.href = url;
  }

  async logout(): Promise<void> {
    await serverLogout();
  }
}

export const authService = new AuthService();

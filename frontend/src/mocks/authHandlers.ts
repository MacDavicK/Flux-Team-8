import { delay, HttpResponse, http } from "msw";
import type {
  AuthStatusResponse,
  LoginRequest,
  LoginResponse,
  SignupRequest,
  SignupResponse,
  User,
} from "~/types";

const MOCK_EMAIL = "test@test.com";
const MOCK_PASSWORD = "test@123";

let currentUser: User | undefined;

const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const validatePassword = (password: string): boolean => {
  return password.length >= 6;
};

export const authHandlers = [
  http.post("/api/auth/login", async ({ request }) => {
    await delay(500);

    const body = (await request.json()) as LoginRequest;
    const { email, password } = body;

    if (!validateEmail(email)) {
      return HttpResponse.json(
        {
          success: false,
          message: "Please enter a valid email address",
        } as LoginResponse,
        { status: 400 },
      );
    }

    if (!validatePassword(password)) {
      return HttpResponse.json(
        {
          success: false,
          message: "Password must be at least 6 characters",
        } as LoginResponse,
        { status: 400 },
      );
    }

    if (email !== MOCK_EMAIL || password !== MOCK_PASSWORD) {
      return HttpResponse.json(
        {
          success: false,
          message: "Invalid email or password",
        } as LoginResponse,
        { status: 401 },
      );
    }

    const user: User = {
      id: "user-1",
      name: "Test User",
      email: MOCK_EMAIL,
      onboarded: false,
      createdAt: new Date().toISOString(),
    };

    currentUser = user;

    const response: LoginResponse = {
      success: true,
      user,
      token: "flux_auth_token_value",
    };

    return new HttpResponse(JSON.stringify(response), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie":
          "flux_auth_token=flux_auth_token_value; Path=/; Max-Age=120; SameSite=Strict",
      },
    });
  }),

  http.post("/api/auth/signup", async ({ request }) => {
    await delay(500);

    const body = (await request.json()) as SignupRequest;
    const { name, email, password } = body;

    if (!name || name.trim().length < 2) {
      return HttpResponse.json(
        {
          success: false,
          message: "Name must be at least 2 characters",
        } as SignupResponse,
        { status: 400 },
      );
    }

    if (!validateEmail(email)) {
      return HttpResponse.json(
        {
          success: false,
          message: "Please enter a valid email address",
        } as SignupResponse,
        { status: 400 },
      );
    }

    if (!validatePassword(password)) {
      return HttpResponse.json(
        {
          success: false,
          message: "Password must be at least 6 characters",
        } as SignupResponse,
        { status: 400 },
      );
    }

    const user: User = {
      id: `user-${Date.now()}`,
      name: name.trim(),
      email,
      onboarded: false,
      createdAt: new Date().toISOString(),
    };

    currentUser = user;

    const response: SignupResponse = {
      success: true,
      user,
      token: "flux_auth_token_value",
    };

    return new HttpResponse(JSON.stringify(response), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie":
          "flux_auth_token=flux_auth_token_value; Path=/; Max-Age=120; SameSite=Strict",
      },
    });
  }),

  http.post("/api/auth/logout", async () => {
    await delay(200);
    currentUser = undefined;

    return new HttpResponse(null, {
      status: 200,
      headers: {
        "Set-Cookie": "flux_auth_token=; Path=/; Max-Age=0",
      },
    });
  }),

  http.get("/api/auth/status", async ({ cookies }) => {
    await delay(200);

    const hasAuthCookie = cookies.flux_auth_token === "flux_auth_token_value";

    if (!hasAuthCookie || !currentUser) {
      return HttpResponse.json({
        isAuthenticated: false,
      } as AuthStatusResponse);
    }

    return HttpResponse.json({
      isAuthenticated: true,
      user: currentUser,
      hasTasks: false,
    } as AuthStatusResponse);
  }),
];

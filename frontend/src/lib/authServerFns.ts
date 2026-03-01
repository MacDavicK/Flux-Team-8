// SERVER-ONLY auth operations as TanStack Start server functions.
// Supabase keys stay in process.env — never bundled into client JS.
import { createServerFn } from "@tanstack/react-start";
import { deleteCookie } from "@tanstack/react-start/server";
import { getServerSupabaseClient } from "./supabaseServer";

type ServerUser = {
  id: string;
  name: string;
  email: string;
  avatar: string | undefined;
};

function extractUser(supabaseUser: {
  id: string;
  email?: string;
  user_metadata: Record<string, unknown>;
  created_at: string;
}): ServerUser {
  const m = supabaseUser.user_metadata;
  return {
    id: supabaseUser.id,
    name:
      (m.name as string | undefined) ??
      (m.full_name as string | undefined) ??
      supabaseUser.email ??
      "User",
    email: supabaseUser.email ?? "",
    avatar: m.avatar_url as string | undefined,
  };
}

export const serverLogin = createServerFn({ method: "POST" })
  .inputValidator((d: { email: string; password: string }) => d)
  .handler(async ({ data }) => {
    const { data: result, error } =
      await getServerSupabaseClient().auth.signInWithPassword(data);
    if (error || !result.user) {
      throw new Error(error?.message ?? "Login failed");
    }
    // @supabase/ssr automatically writes session to httpOnly cookie via setAll
    return { user: extractUser(result.user) };
  });

export const serverSignup = createServerFn({ method: "POST" })
  .inputValidator((d: { name: string; email: string; password: string }) => d)
  .handler(async ({ data }) => {
    const { data: result, error } = await getServerSupabaseClient().auth.signUp(
      {
        email: data.email,
        password: data.password,
        options: { data: { name: data.name } },
      },
    );
    if (error || !result.user) {
      throw new Error(error?.message ?? "Signup failed");
    }
    return { user: extractUser(result.user) };
  });

export const serverLogout = createServerFn({ method: "POST" }).handler(
  async () => {
    await getServerSupabaseClient().auth.signOut();
    // @supabase/ssr calls setAll with expired cookies on signOut.
    // Belt-and-suspenders: also explicitly clear known Supabase cookie names.
    deleteCookie("sb-yhvrwwdvyvaztipunbvh-auth-token", { path: "/" });
    deleteCookie("sb-yhvrwwdvyvaztipunbvh-auth-token-code-verifier", {
      path: "/",
    });
  },
);

/**
 * Reads the current session from the httpOnly cookie (server-side) and returns
 * the access token + user info. Called once on React mount to hydrate the
 * in-memory token in apiClient.ts — no token is ever stored in localStorage.
 */
export const serverGetAccessToken = createServerFn({ method: "GET" }).handler(
  async () => {
    const client = getServerSupabaseClient();

    // getUser() authenticates against the Supabase Auth server — safe to trust.
    const { data: userData, error: userError } = await client.auth.getUser();
    if (userError || !userData.user) {
      return { token: null as string | null, user: null as ServerUser | null };
    }

    // getSession() is only used here to retrieve the access token string for the
    // FastAPI backend. We do NOT use session.user — userData.user is authoritative.
    const { data: sessionData } = await client.auth.getSession();

    return {
      token: (sessionData.session?.access_token ?? null) as string | null,
      user: extractUser(userData.user) as ServerUser | null,
    };
  },
);

/**
 * Generates a Google OAuth redirect URL server-side (keys hidden from client).
 * The client receives the URL string and navigates to it via window.location.href.
 */
export const serverGetGoogleOAuthUrl = createServerFn({
  method: "GET",
}).handler(async () => {
  const { data, error } = await getServerSupabaseClient().auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${process.env.APP_URL ?? "http://localhost:3000"}/auth/callback`,
      skipBrowserRedirect: true,
    },
  });
  if (error || !data.url) {
    throw new Error(error?.message ?? "Failed to generate Google OAuth URL");
  }
  return { url: data.url };
});

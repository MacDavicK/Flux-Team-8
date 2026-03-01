import { createFileRoute, redirect } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { getServerSupabaseClient } from "~/lib/supabaseServer";

// Server function: exchanges the OAuth authorization code for a session.
// Runs on the TanStack Start server — Supabase keys never reach the client.
// @supabase/ssr writes the session as httpOnly cookies automatically.
const exchangeOAuthCode = createServerFn({ method: "GET" })
  .inputValidator((d: { code: string }) => d)
  .handler(async ({ data }) => {
    const { error } = await getServerSupabaseClient().auth.exchangeCodeForSession(data.code);
    if (error) {
      throw new Error(error.message);
    }
  });

export const Route = createFileRoute("/auth/callback")({
  // The loader runs on the server during SSR, before any HTML is sent.
  // It reads ?code= from the URL, exchanges it server-side, sets the httpOnly
  // session cookie, then issues an HTTP 302 redirect — no client-side JS needed.
  loader: async ({ location }) => {
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    const error = params.get("error");

    if (error) {
      throw redirect({ to: "/login" });
    }

    if (!code) {
      throw redirect({ to: "/login" });
    }

    await exchangeOAuthCode({ data: { code } });
    throw redirect({ to: "/" });
  },

  component: AuthCallbackPage,
});

// This component only renders if the loader did not redirect (e.g. slow network).
function AuthCallbackPage() {
  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center p-4">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-sage/30 border-t-sage rounded-full animate-spin mx-auto mb-4" />
        <p className="text-river text-sm">Completing sign in...</p>
      </div>
    </div>
  );
}

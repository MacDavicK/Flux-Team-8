/// <reference types="vite/client" />
import {
  createRootRoute,
  HeadContent,
  Scripts,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DefaultCatchBoundary } from "~/components/DefaultCatchBoundary";
import { NotFound } from "~/components/NotFound";
import { SplashScreen } from "~/components/splash/SplashScreen";
import { AuthProvider, useAuth } from "~/contexts/AuthContext";
import appCss from "~/styles/app.css?url";
import { seo } from "~/utils/seo";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      ...seo({
        title: "Flux - Calendar & Goal Assistant",
        description:
          "A calendar and goal-setting assistant with organic glassmorphism design.",
      }),
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      {
        rel: "apple-touch-icon",
        sizes: "180x180",
        href: "/apple-touch-icon.png",
      },
      {
        rel: "icon",
        type: "image/png",
        sizes: "32x32",
        href: "/favicon-32x32.png",
      },
      {
        rel: "icon",
        type: "image/png",
        sizes: "16x16",
        href: "/favicon-16x16.png",
      },
      { rel: "manifest", href: "/site.webmanifest", color: "#fffff" },
      { rel: "icon", href: "/favicon.ico" },
    ],
  }),
  errorComponent: DefaultCatchBoundary,
  notFoundComponent: () => <NotFound />,
  shellComponent: RootShell,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <RootDocument>{children}</RootDocument>
    </AuthProvider>
  );
}

function RootDocument({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [showSplash, setShowSplash] = useState(true);
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  // Redirect as soon as auth resolves — do NOT wait for splash to finish.
  // Splash is purely visual and should not gate the auth decision.
  useEffect(() => {
    if (authLoading) return;

    const currentPath = window.location.pathname;

    if (!isAuthenticated && currentPath !== "/login") {
      navigate({ to: "/login" });
    } else if (
      isAuthenticated &&
      user &&
      !user.onboarded &&
      currentPath !== "/onboarding"
    ) {
      navigate({ to: "/onboarding" });
    }
  }, [authLoading, isAuthenticated, user, navigate]);

  // Keep the service worker push listener alive so notifications are handled
  // while the app is in the foreground.
  useEffect(() => {
    if (typeof window === "undefined") return;
    let cleanup: (() => void) | undefined;
    import("~/lib/pushNotifications").then(({ listenForInAppPushes }) => {
      cleanup = listenForInAppPushes(() => {
        // Push notifications are handled natively by the service worker.
        // Add in-app banner logic here if needed in the future.
      });
    });
    return () => cleanup?.();
  }, []);

  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {showSplash && (
          <SplashScreen
            onComplete={() => setShowSplash(false)}
            minDuration={3000}
          />
        )}
        <main className="relative min-h-screen overflow-x-hidden w-full max-w-md mx-auto">
          {children}
        </main>
        <Scripts />
      </body>
    </html>
  );
}

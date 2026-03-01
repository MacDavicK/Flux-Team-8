/// <reference types="vite/client" />
import {
  createRootRoute,
  HeadContent,
  Scripts,
  useLocation,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DefaultCatchBoundary } from "~/components/DefaultCatchBoundary";
import { DemoPanel } from "~/components/demo/DemoPanel";
import { NotificationCenter } from "~/components/demo/NotificationCenter";
import { DemoButton } from "~/components/flow/v2/DemoButton";
import { NotFound } from "~/components/NotFound";
import { SplashScreen } from "~/components/splash/SplashScreen";
import { AuthProvider, useAuth } from "~/contexts/AuthContext";
import {
  SimulationProvider,
  useSimulation,
} from "~/contexts/SimulationContext";
import { demoService } from "~/services/DemoService";
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
      <SimulationProvider>
        <RootDocument>{children}</RootDocument>
      </SimulationProvider>
    </AuthProvider>
  );
}

import { FluxNotificationModal } from "~/components/modals/FluxNotificationModal";

function RootDocument({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isDemoOpen, setIsDemoOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const { addNotification, setEscalationSpeed, startEscalation } =
    useSimulation();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  const isFlowPage = location.pathname === "/";
  const showDemoUI = isFlowPage && !showSplash;

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
      currentPath !== "/chat"
    ) {
      navigate({ to: "/chat" });
    }
  }, [authLoading, isAuthenticated, user, navigate]);

  const handleSplashComplete = () => {
    setShowSplash(false);
  };

  const handleSimulateLeavingHome = async () => {
    const raw = await demoService.triggerLocation();
    const response = { message: String(raw.message ?? "You're out!"), type: "notification" as const };
    addNotification(response);
    startEscalation();
  };

  const handleSimulateNearStore = async () => {
    const raw = await demoService.triggerLocation();
    const response = { message: String(raw.message ?? "You're near a store!"), type: "notification" as const };
    addNotification(response);
    startEscalation();
  };

  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {showSplash && (
          <SplashScreen onComplete={handleSplashComplete} minDuration={3000} />
        )}
        <main className="relative min-h-screen overflow-x-hidden">
          {children}

          {showDemoUI && (
            <>
              <NotificationCenter />

              <DemoButton onClick={() => setIsDemoOpen(true)} />

              <DemoPanel
                isOpen={isDemoOpen}
                onClose={() => setIsDemoOpen(false)}
                onTimeWarp={() => {
                  setIsDemoOpen(false);
                  setIsNotificationOpen(true);
                }}
                onTravelMode={() => console.log("Travel mode activated")}
                onSimulateLeavingHome={handleSimulateLeavingHome}
                onSimulateNearStore={handleSimulateNearStore}
                onEscalationSpeedChange={setEscalationSpeed}
              />

              <FluxNotificationModal
                isOpen={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
              />
            </>
          )}
        </main>
        <Scripts />
      </body>
    </html>
  );
}

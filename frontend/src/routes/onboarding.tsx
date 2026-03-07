import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { OnboardingChat } from "~/components/onboarding/OnboardingChat";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { serverGetMe } from "~/lib/authServerFns";
import { setInMemoryToken } from "~/lib/apiClient";

export const Route = createFileRoute("/onboarding")({
  pendingComponent: () => (
    <div className="relative min-h-screen flex flex-col items-center justify-center">
      <AmbientBackground variant="dark" />
      <LoadingState />
    </div>
  ),
  pendingMs: 0,
  loader: async () => {
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    if (user.onboarded) throw redirect({ to: "/chat" });
    setInMemoryToken(token);
    return { user };
  },
  component: OnboardingPage,
});

function getGreeting(name?: string): string {
  const hour = new Date().getHours();
  const salutation = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation;
}

function OnboardingPage() {
  const navigate = useNavigate();
  const { user } = Route.useLoaderData();

  return (
    <div className="relative h-screen flex flex-col overflow-hidden">
      <AmbientBackground variant="dark" />

      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-12 pb-3 relative z-10">
        <h1 className="font-display italic text-xl text-charcoal/80">
          {getGreeting(user?.name)}
        </h1>
      </div>

      <OnboardingChat onComplete={() => navigate({ to: "/chat" })} />
    </div>
  );
}

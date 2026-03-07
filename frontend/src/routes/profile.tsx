import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useState } from "react";
import { BottomNav } from "~/components/navigation/BottomNav";
import { ProfileHeader } from "~/components/reflection/ProfileHeader";
import { ProfilePreferences } from "~/components/profile/ProfilePreferences";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { useAuth } from "~/contexts/AuthContext";
import { serverGetMe } from "~/lib/authServerFns";
import { accountService } from "~/services/AccountService";
import type { AccountMe, AccountPatchRequest } from "~/types";
import { debugSsrLog, isClient } from "~/utils/env";

function ProfilePagePending() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <AmbientBackground />
      <LoadingState />
    </div>
  );
}

export const Route = createFileRoute("/profile")({
  pendingComponent: ProfilePagePending,
  pendingMs: 0,
  loader: async () => {
    if (isClient()) {
      const account = await accountService.getMe();
      const data = { account };
      debugSsrLog("/profile (ProfilePage)", data);
      return data;
    }
    // Server-side: use serverGetMe for token, then fetch with absolute URL
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    const res = await fetch(`${backendUrl}/api/v1/account/me`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const account: AccountMe = res.ok ? await res.json() : ({} as AccountMe);
    return { account };
  },
  component: ProfilePage,
});

function ProfilePage() {
  const { account: initialAccount } = Route.useLoaderData();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState<AccountMe>(initialAccount as AccountMe);
  const [isSaving, setIsSaving] = useState(false);

  const displayName =
    (account as AccountMe & { profile?: { name?: string } })?.profile?.name ??
    user?.name ??
    account?.name ??
    account?.email ??
    "You";

  const handlePatch = async (patch: AccountPatchRequest) => {
    setIsSaving(true);
    try {
      const updated = await accountService.patchMe(patch);
      setAccount(updated as unknown as AccountMe);
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });
  };

  return (
    <div className="min-h-screen pb-32">
      <AmbientBackground />

      <ProfileHeader name={displayName} avatarUrl={undefined} />

      {isSaving && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50 glass-bubble px-4 py-2 text-xs font-semibold text-sage"
        >
          Saving…
        </motion.div>
      )}

      <ProfilePreferences
        account={account}
        onPatch={handlePatch}
        onLogout={handleLogout}
      />

      <BottomNav />
    </div>
  );
}

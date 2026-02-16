import type { User } from "~/types/user";
import { ColorTheme } from "~/types/user";

// Sample user for demo purposes
export const currentUser: User = {
  id: "1",
  name: "Demo User",
  email: "demo@flux.app",
  avatar: undefined,
  preferences: {
    theme: ColorTheme.SAGE,
    notifications: true,
    emailDigest: "weekly",
    timezone: "America/New_York",
    language: "en",
  },
};

export type { User };
export { ColorTheme } from "~/types/user";

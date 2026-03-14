import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiFetch, setInMemoryToken } from "~/lib/apiClient";
import { serverGetMe } from "~/lib/authServerFns";
import { authService } from "~/services/AuthService";
import type { User } from "~/types";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | undefined;
  hasTasks: boolean;
  login: (email: string, password: string) => Promise<User | undefined>;
  signup: (
    name: string,
    email: string,
    password: string,
  ) => Promise<User | undefined>;
  logout: () => Promise<void>;
  refreshAuthStatus: () => Promise<User | undefined>;
  loginWithGoogle: () => Promise<void>;
  patchUser: (patch: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | undefined>(undefined);
  const [hasTasks, setHasTasks] = useState(false);

  /**
   * Reads the session from the httpOnly cookie and fetches the authoritative
   * profile from the FastAPI backend — all in a single server-side round-trip
   * via serverGetMe. Hydrates the in-memory token on the client.
   */
  const refreshAuthStatus = useCallback(async (): Promise<User | undefined> => {
    setIsLoading(true);
    try {
      const { token, user: serverUser, sessionInvalid } = await serverGetMe();

      if (sessionInvalid || !token || !serverUser) {
        setInMemoryToken(null);
        setIsAuthenticated(false);
        setUser(undefined);
        setHasTasks(false);
        return undefined;
      }

      setInMemoryToken(token);
      setIsAuthenticated(true);
      setUser(serverUser);

      // Silently re-register push subscription for users who already granted permission.
      // Dynamic import keeps this out of the SSR path.
      if (typeof window !== "undefined") {
        import("~/lib/pushNotifications").then(({ registerAndSubscribe }) => {
          registerAndSubscribe().catch(() => {
            /* non-critical */
          });
        });
      }

      return serverUser;
    } catch {
      setInMemoryToken(null);
      setIsAuthenticated(false);
      setUser(undefined);
      setHasTasks(false);
      return undefined;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Hydrate auth state on mount.
  useEffect(() => {
    refreshAuthStatus();
  }, [refreshAuthStatus]);

  // Silently sync browser timezone to backend if it differs from stored value.
  useEffect(() => {
    if (!user) return;
    const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (browserTz && browserTz !== user.timezone) {
      apiFetch("/api/v1/account/me", {
        method: "PATCH",
        body: JSON.stringify({ timezone: browserTz }),
      })
        .then(() => {
          setUser((prev) => (prev ? { ...prev, timezone: browserTz } : prev));
        })
        .catch(() => {
          /* silent — non-critical */
        });
    }
  }, [user?.id, user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Periodically refresh to keep the in-memory token fresh before it expires.
  // Supabase JWTs expire after 1 hour; refresh every 45 minutes.
  useEffect(() => {
    const interval = setInterval(refreshAuthStatus, 45 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshAuthStatus]);

  const login = useCallback(
    async (email: string, password: string): Promise<User | undefined> => {
      // serverLogin (called inside authService.login) sets the httpOnly cookie.
      // refreshAuthStatus then reads it to hydrate the in-memory token.
      await authService.login({ email, password });
      return refreshAuthStatus();
    },
    [refreshAuthStatus],
  );

  const signup = useCallback(
    async (
      name: string,
      email: string,
      password: string,
    ): Promise<User | undefined> => {
      await authService.signup({ name, email, password });
      return refreshAuthStatus();
    },
    [refreshAuthStatus],
  );

  const logout = useCallback(async () => {
    // Unsubscribe from push notifications before signing out so the backend
    // stops sending notifications to this device.
    try {
      const { unsubscribe } = await import("~/lib/pushNotifications");
      await unsubscribe();
    } catch {
      // Non-fatal — proceed with logout even if unsubscribe fails.
    }
    await authService.logout();
    setInMemoryToken(null);
    setIsAuthenticated(false);
    setUser(undefined);
    setHasTasks(false);
  }, []);

  const loginWithGoogle = useCallback(async () => {
    await authService.loginWithGoogle();
    // Browser navigates away — no state update needed here.
    // State is restored when /auth/callback completes and refreshAuthStatus() runs.
  }, []);

  const patchUser = useCallback((patch: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        user,
        hasTasks,
        login,
        signup,
        logout,
        refreshAuthStatus,
        loginWithGoogle,
        patchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

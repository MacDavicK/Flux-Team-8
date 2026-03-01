import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { setInMemoryToken } from "~/lib/apiClient";
import { serverGetAccessToken } from "~/lib/authServerFns";
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
   * Reads the session from the httpOnly cookie (via server function), hydrates
   * the in-memory token, then fetches the onboarded flag from the backend.
   */
  const refreshAuthStatus = useCallback(async (): Promise<User | undefined> => {
    setIsLoading(true);
    try {
      const { token, user: serverUser } = await serverGetAccessToken();
      setInMemoryToken(token);

      if (!token || !serverUser) {
        setIsAuthenticated(false);
        setUser(undefined);
        setHasTasks(false);
        return undefined;
      }

      // Fetch authoritative onboarded flag from the backend.
      // A 401 here means the session is invalid/expired — treat as logged out.
      // Token is now available in memory so apiFetch would work, but using raw
      // fetch here avoids a circular import with apiClient.
      let onboarded = false;
      let profileName: string | null = null;
      try {
        const res = await fetch("/api/v1/account/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.status === 401 || res.status === 403) {
          // Session rejected by the backend — clear everything.
          setInMemoryToken(null);
          setIsAuthenticated(false);
          setUser(undefined);
          setHasTasks(false);
          return undefined;
        }
        if (res.ok) {
          const meData = (await res.json()) as {
            onboarded: boolean;
            name?: string | null;
          };
          onboarded = meData.onboarded ?? false;
          profileName = meData.name ?? null;
        }
      } catch {
        // Backend unavailable — keep onboarded: false as safe default.
        // Do not log out; the backend may just be temporarily down.
      }

      const resolvedUser: User = {
        ...serverUser,
        onboarded,
        ...(profileName ? { name: profileName } : {}),
      };
      setIsAuthenticated(true);
      setUser(resolvedUser);
      return resolvedUser;
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

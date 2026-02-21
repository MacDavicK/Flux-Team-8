import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { authService } from "~/services/AuthService";
import type { AuthStatusResponse, User } from "~/types";

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | undefined;
  hasTasks: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuthStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [isAuthenticated, setIsAuthenticated] = useState(
    authService.isAuthenticated(),
  );
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | undefined>(undefined);
  const [hasTasks, setHasTasks] = useState(false);

  const refreshAuthStatus = useCallback(async () => {
    setIsLoading(true);
    try {
      const status: AuthStatusResponse = await authService.getAuthStatus();
      setIsAuthenticated(status.isAuthenticated);
      setUser(status.user);
      setHasTasks(status.hasTasks ?? false);
    } catch {
      setIsAuthenticated(false);
      setUser(undefined);
      setHasTasks(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAuthStatus();
  }, [refreshAuthStatus]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authService.login({ email, password });
    setIsAuthenticated(true);
    setUser(response.user);
    setHasTasks(false);
  }, []);

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      const response = await authService.signup({ name, email, password });
      setIsAuthenticated(true);
      setUser(response.user);
      setHasTasks(false);
    },
    [],
  );

  const logout = useCallback(async () => {
    await authService.logout();
    setIsAuthenticated(false);
    setUser(undefined);
    setHasTasks(false);
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

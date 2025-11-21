import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from "react";
import type { User, LoginRequest, RegisterRequest } from "../types/auth";
import { authApi } from "../api/auth";
import { tokenStorage } from "../utils/auth/token-storage";
import {
  setupTokenRefresh,
  clearTokenRefresh,
} from "../utils/auth/token-refresh";
import { logger } from "../utils/logger";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize auth state from storage
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = tokenStorage.getToken();
        const storedUser = tokenStorage.getUser();

        if (token && storedUser) {
          // Verify token is still valid by fetching current user
          try {
            const currentUser = await authApi.getCurrentUser();
            setUser(currentUser);
            setIsAuthenticated(true);
            tokenStorage.setUser(currentUser);
          } catch (err) {
            // Token invalid, clear storage
            tokenStorage.clear();
            setUser(null);
            setIsAuthenticated(false);
          }
        }
      } catch (err) {
        logger.error("Auth initialization error:", err);
        tokenStorage.clear();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    try {
      setError(null);
      setIsLoading(true);
      const response = await authApi.login(credentials);

      tokenStorage.setToken(response.token);
      tokenStorage.setUser(response.user);
      setUser(response.user);
      setIsAuthenticated(true);

      // Setup automatic token refresh
      setupTokenRefresh(response.expires_in);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        "Login failed. Please check your credentials.";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    try {
      setError(null);
      setIsLoading(true);
      const response = await authApi.register(data);

      tokenStorage.setToken(response.token);
      tokenStorage.setUser(response.user);
      setUser(response.user);
      setIsAuthenticated(true);

      // Setup automatic token refresh
      setupTokenRefresh(response.expires_in);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || "Registration failed. Please try again.";
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (err) {
      logger.error("Logout error:", err);
    } finally {
      tokenStorage.clear();
      clearTokenRefresh();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      tokenStorage.setUser(currentUser);
    } catch (err) {
      logger.error("Failed to refresh user:", err);
      // If refresh fails, user might be logged out
      tokenStorage.clear();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const contextValue = useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      error,
      login,
      register,
      logout,
      refreshUser,
      clearError,
    }),
    [
      user,
      isAuthenticated,
      isLoading,
      error,
      login,
      register,
      logout,
      refreshUser,
      clearError,
    ],
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

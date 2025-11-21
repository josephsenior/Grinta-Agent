import { authApi } from "../../api/auth";
import { tokenStorage } from "./token-storage";
import { logger } from "../logger";

let refreshTimer: NodeJS.Timeout | null = null;

/**
 * Setup automatic token refresh
 */
export function setupTokenRefresh(expiresIn: number): void {
  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  // Refresh token 5 minutes before expiration
  const refreshTime = (expiresIn - 300) * 1000; // Convert to milliseconds

  if (refreshTime > 0) {
    refreshTimer = setTimeout(async () => {
      try {
        const { token, expires_in: newExpiresIn } =
          await authApi.refreshToken();
        tokenStorage.setToken(token);
        setupTokenRefresh(newExpiresIn); // Setup next refresh
      } catch (error) {
        logger.error("Token refresh failed:", error);
        // Token refresh failed, user will need to login again
        tokenStorage.clear();
        if (
          typeof window !== "undefined" &&
          window.location.pathname !== "/auth/login"
        ) {
          window.location.href = "/auth/login";
        }
      }
    }, refreshTime);
  }
}

/**
 * Clear token refresh timer
 */
export function clearTokenRefresh(): void {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

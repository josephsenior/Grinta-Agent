import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../context/auth-context";
import type { UserRole } from "../../../utils/auth/permissions";

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireRole?: UserRole;
  redirectTo?: string;
}

/**
 * AuthGuard component to protect routes
 *
 * @param requireAuth - If true, redirects to login if not authenticated
 * @param requireRole - If specified, only allows users with this role
 * @param redirectTo - Custom redirect path (default: /auth/login)
 */
export function AuthGuard({
  children,
  requireAuth = true,
  requireRole,
  redirectTo = "/auth/login",
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoading) return;

    // Check authentication requirement
    if (requireAuth && !isAuthenticated) {
      // Save current location for redirect after login
      const currentPath = window.location.pathname + window.location.search;
      navigate(`${redirectTo}?redirect=${encodeURIComponent(currentPath)}`);
      return;
    }

    // Check role requirement
    if (requireRole && user && user.role !== requireRole) {
      navigate("/"); // Redirect to home if role doesn't match
    }
  }, [
    isAuthenticated,
    isLoading,
    requireAuth,
    requireRole,
    user,
    navigate,
    redirectTo,
  ]);

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-gray-100" />
      </div>
    );
  }

  // Don't render children if auth requirements not met
  if (requireAuth && !isAuthenticated) {
    return null;
  }

  if (requireRole && user && user.role !== requireRole) {
    return null;
  }

  return children as React.ReactElement;
}

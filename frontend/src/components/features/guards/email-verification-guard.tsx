import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useSettings } from "#/hooks/query/use-settings";

/**
 * A component that restricts access to routes based on email verification status.
 * If EMAIL_VERIFIED is false, only allows access to the /settings/user page.
 */
export function EmailVerificationGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: settings, isLoading } = useSettings();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  React.useEffect(() => {
    // If settings are still loading, don't do anything yet
    if (isLoading) {
      return;
    }

    // If EMAIL_VERIFIED is explicitly false (not undefined or null)
    if (settings?.EMAIL_VERIFIED === false && pathname !== "/settings/user") {
      navigate("/settings/user", { replace: true });
    }
  }, [settings?.EMAIL_VERIFIED, pathname, navigate, isLoading]);

  return children;
}

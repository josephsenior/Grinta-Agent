import { useEffect } from "react";
import { useConfig } from "./query/use-config";
import { useIsAuthed } from "./query/use-is-authed";
import { getLoginMethod, LoginMethod } from "#/utils/local-storage";
import { useAuthUrl } from "./use-auth-url";

// Helper function to get auth URL for a specific provider
const useProviderAuthUrl = (provider: string, config: any) =>
  useAuthUrl({
    appMode: config?.APP_MODE || null,
    identityProvider: provider,
    authUrl: config?.AUTH_URL,
  });

// Helper function to check if auto-login conditions are met
const shouldPerformAutoLogin = (
  config: any,
  isConfigLoading: boolean | undefined,
  isAuthLoading: boolean | undefined,
  isAuthed: boolean | undefined,
  loginMethod: string | null,
): boolean =>
  config?.APP_MODE === "saas" &&
  !isConfigLoading &&
  !isAuthLoading &&
  !isAuthed &&
  loginMethod !== null &&
  loginMethod !== undefined;

// Helper function to get the appropriate auth URL
const getAuthUrlForMethod = (
  loginMethod: string | null,
  authUrls: Record<string, string | null>,
): string | null => (loginMethod ? authUrls[loginMethod] || null : null);

// Helper function to perform the redirect
const redirectToAuth = (authUrl: string, loginMethod: string) => {
  const url = new URL(authUrl);
  url.searchParams.append("login_method", loginMethod);
  window.location.href = url.toString();
};

/**
 * Hook to automatically log in the user if they have a login method stored in local storage
 * Only works in SAAS mode and when the user is not already logged in
 */
export const useAutoLogin = () => {
  const { data: config, isLoading: isConfigLoading } = useConfig();
  const { data: isAuthed, isLoading: isAuthLoading } = useIsAuthed();
  const loginMethod = getLoginMethod();

  // Get auth URLs for all providers
  const authUrls = {
    [LoginMethod.GITHUB]: useProviderAuthUrl("github", config),
    [LoginMethod.GITLAB]: useProviderAuthUrl("gitlab", config),
    [LoginMethod.BITBUCKET]: useProviderAuthUrl("bitbucket", config),
    [LoginMethod.ENTERPRISE_SSO]: useProviderAuthUrl("enterprise_sso", config),
  };

  useEffect(() => {
    if (
      !shouldPerformAutoLogin(
        config,
        isConfigLoading,
        isAuthLoading,
        isAuthed,
        loginMethod,
      )
    ) {
      return;
    }

    const authUrl = getAuthUrlForMethod(loginMethod, authUrls);
    if (authUrl && loginMethod) {
      redirectToAuth(authUrl, loginMethod);
    }
  }, [
    config?.APP_MODE,
    isAuthed,
    isConfigLoading,
    isAuthLoading,
    loginMethod,
    authUrls[LoginMethod.GITHUB],
    authUrls[LoginMethod.GITLAB],
    authUrls[LoginMethod.BITBUCKET],
    authUrls[LoginMethod.ENTERPRISE_SSO],
  ]);
};

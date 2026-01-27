import { useConfig } from "#/hooks/query/use-config";
import { useIsAuthed } from "#/hooks/query/use-is-authed";
import { useUserProviders } from "./use-user-providers";

/**
 * Hook to determine if user-related features should be shown or enabled.
 * Returns true if the user is authenticated and the application mode allows it.
 *
 * @returns boolean indicating if user features should be shown
 */
export const useShouldShowUserFeatures = (): boolean => {
  const { data: config } = useConfig();
  const { data: isAuthed } = useIsAuthed();
  const { providers } = useUserProviders();

  if (!config) return false;
  if (!isAuthed) return false;

  if (config.APP_MODE === "oss") {
    return providers.length > 0;
  }

  return true;
};

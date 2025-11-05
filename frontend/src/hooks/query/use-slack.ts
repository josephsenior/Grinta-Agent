/**
 * React Query hooks for Slack integration
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  listSlackWorkspaces,
  getSlackInstallUrl,
  uninstallSlackWorkspace,
  type SlackWorkspace,
  type SlackInstallResponse,
} from "#/api/slack";

const QUERY_KEYS = {
  workspaces: ["slack", "workspaces"] as const,
};

/**
 * Hook to fetch all installed Slack workspaces
 */
export function useSlackWorkspaces(): UseQueryResult<SlackWorkspace[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.workspaces,
    queryFn: listSlackWorkspaces,
  });
}

/**
 * Hook to install Slack workspace
 */
export function useInstallSlackWorkspace(): UseMutationResult<
  SlackInstallResponse,
  Error,
  { redirect_url?: string } | undefined
> {
  return useMutation({
    mutationFn: getSlackInstallUrl,
  });
}

/**
 * Hook to uninstall Slack workspace
 */
export function useUninstallSlackWorkspace(): UseMutationResult<
  void,
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uninstallSlackWorkspace,
    onSuccess: () => {
      // Invalidate workspaces query to refetch
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workspaces });
    },
  });
}


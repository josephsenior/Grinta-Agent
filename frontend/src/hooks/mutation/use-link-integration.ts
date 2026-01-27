import { useMutation, useQueryClient } from "@tanstack/react-query";
import IntegrationsClient from "#/api/integrations";

interface UseLinkIntegrationOptions {
  onSettled?: () => void;
}

export function useLinkIntegration(platform: string, options?: UseLinkIntegrationOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (workspace: string) => IntegrationsClient.linkIntegration(platform, workspace),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-status", platform] });
      options?.onSettled?.();
    },
  });
}

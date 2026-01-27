import { useMutation, useQueryClient } from "@tanstack/react-query";
import IntegrationsClient from "#/api/integrations";

interface UseConfigureIntegrationOptions {
  onSettled?: () => void;
}

export function useConfigureIntegration(platform: string, options?: UseConfigureIntegrationOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      workspace: string;
      webhookSecret: string;
      serviceAccountEmail: string;
      serviceAccountApiKey: string;
      isActive: boolean;
    }) => IntegrationsClient.configureIntegration(platform, data),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-status", platform] });
      options?.onSettled?.();
    },
  });
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import IntegrationsClient from "#/api/integrations";

interface UseUnlinkIntegrationOptions {
  onSettled?: () => void;
}

export function useUnlinkIntegration(platform: string, options?: UseUnlinkIntegrationOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => IntegrationsClient.unlinkIntegration(platform),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["integration-status", platform] });
      options?.onSettled?.();
    },
  });
}

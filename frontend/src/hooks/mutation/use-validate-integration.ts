import { useMutation } from "@tanstack/react-query";
import IntegrationsClient from "#/api/integrations";

interface UseValidateIntegrationOptions {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

export function useValidateIntegration(platform: string, options?: UseValidateIntegrationOptions) {
  return useMutation({
    mutationFn: (workspace: string) => IntegrationsClient.validateIntegration(platform, workspace),
    onSuccess: (data) => {
      options?.onSuccess?.(data);
    },
    onError: (error) => {
      options?.onError?.(error);
    },
  });
}

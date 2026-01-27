import { useQuery } from "@tanstack/react-query";
import IntegrationsClient from "#/api/integrations";

export function useIntegrationStatus(platform: string) {
  return useQuery({
    queryKey: ["integration-status", platform],
    queryFn: () => IntegrationsClient.getIntegrationStatus(platform),
  });
}

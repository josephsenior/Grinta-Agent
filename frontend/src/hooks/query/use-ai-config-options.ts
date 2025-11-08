import { useQuery } from "@tanstack/react-query";
import Forge from "#/api/forge";

const fetchAiConfigOptions = async () => ({
  models: await Forge.getModels(),
  agents: await Forge.getAgents(),
  securityAnalyzers: await Forge.getSecurityAnalyzers(),
});

export const useAIConfigOptions = () =>
  useQuery({
    queryKey: ["ai-config-options"],
    queryFn: fetchAiConfigOptions,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });

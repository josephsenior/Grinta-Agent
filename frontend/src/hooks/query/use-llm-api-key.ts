import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Forge } from "#/api/forge-axios";
import { useConfig } from "./use-config";

export const LLM_API_KEY_QUERY_KEY = "llm-api-key";

export interface LlmApiKeyResponse {
  key: string | null;
}

export function useLlmApiKey() {
  const { data: config } = useConfig();

  return useQuery({
    queryKey: [LLM_API_KEY_QUERY_KEY],
    enabled: config?.APP_MODE === "saas",
    queryFn: async () => {
      const { data } =
        await Forge.get<LlmApiKeyResponse>("/api/keys/llm/byor");
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

export function useRefreshLlmApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const { data } = await Forge.post<LlmApiKeyResponse>(
        "/api/keys/llm/byor/refresh",
      );
      return data;
    },
    onSuccess: () => {
      // Invalidate the LLM API key query to trigger a refetch
      queryClient.invalidateQueries({ queryKey: [LLM_API_KEY_QUERY_KEY] });
    },
  });
}

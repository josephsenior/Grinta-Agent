import { useQuery } from "@tanstack/react-query";
import Forge from "#/api/forge";
import { Provider } from "#/types/settings";

export function useSearchRepositories(
  query: string,
  selectedProvider?: Provider | null,
  pageSize: number = 3,
) {
  return useQuery({
    queryKey: ["repositories", "search", query, selectedProvider, pageSize],
    queryFn: () =>
      Forge.searchGitRepositories(
        query,
        pageSize,
        selectedProvider || undefined,
      ),
    enabled: !!query && !!selectedProvider,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });
}

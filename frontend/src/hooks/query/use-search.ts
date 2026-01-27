import { useQuery } from "@tanstack/react-query";
import { globalSearch } from "#/api/search";

export const useGlobalSearch = (
  query: string,
  type?: "conversations" | "files" | "all",
  limit?: number,
) => {
  return useQuery({
    queryKey: ["search", "global", query, type, limit],
    queryFn: () => globalSearch(query, type, limit),
    enabled: query.length > 0,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

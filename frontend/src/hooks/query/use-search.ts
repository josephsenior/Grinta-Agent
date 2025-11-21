import { useQuery } from "@tanstack/react-query";
import { globalSearch } from "#/api/search";
import { useIsAuthed } from "./use-is-authed";

export const useGlobalSearch = (
  query: string,
  type?: "conversations" | "snippets" | "files" | "all",
  limit?: number,
) => {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: ["search", "global", query, type, limit],
    queryFn: () => globalSearch(query, type, limit),
    enabled: !!userIsAuthenticated && query.length > 0,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

import { useInfiniteQuery } from "@tanstack/react-query";
import Forge from "#/api/forge";

export const usePaginatedConversations = (limit: number = 20) => {
  return useInfiniteQuery({
    queryKey: ["user", "conversations", "paginated", limit],
    queryFn: ({ pageParam }) => Forge.getUserConversations(limit, pageParam),
    enabled: true,
    getNextPageParam: (lastPage) => lastPage.next_page_id,
    initialPageParam: undefined as string | undefined,
  });
};

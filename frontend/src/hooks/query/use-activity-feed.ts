import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { getActivityFeed } from "#/api/activity";

export const useActivityFeed = (
  page: number = 1,
  limit: number = 20,
  type?: string,
) => {
  return useQuery({
    queryKey: ["activity", "feed", page, limit, type],
    queryFn: () => getActivityFeed(page, limit, type),
    enabled: true,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

export const useInfiniteActivityFeed = (limit: number = 20, type?: string) => {
  return useInfiniteQuery({
    queryKey: ["activity", "feed", "infinite", limit, type],
    queryFn: ({ pageParam = 1 }) => getActivityFeed(pageParam, limit, type),
    enabled: true,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination.has_more) {
        return lastPage.pagination.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

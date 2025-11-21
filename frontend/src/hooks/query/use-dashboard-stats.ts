import { useQuery } from "@tanstack/react-query";
import { getDashboardStats } from "#/api/dashboard";
import { useIsAuthed } from "./use-is-authed";

export const useDashboardStats = (
  recentLimit?: number,
  activityLimit?: number,
) => {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: ["dashboard", "stats", recentLimit, activityLimit],
    queryFn: () => getDashboardStats(recentLimit, activityLimit),
    enabled: !!userIsAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes - dashboard stats don't change frequently
  });
};

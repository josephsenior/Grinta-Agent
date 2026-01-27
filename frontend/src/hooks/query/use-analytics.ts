import { useQuery } from "@tanstack/react-query";
import { getAnalyticsDashboard } from "#/api/analytics";
import type { AnalyticsPeriod } from "#/types/analytics";

export const ANALYTICS_KEYS = {
  dashboard: (period: AnalyticsPeriod) => ["analytics", "dashboard", period] as const,
};

export function useAnalyticsDashboard(period: AnalyticsPeriod = "week") {
  return useQuery({
    queryKey: ANALYTICS_KEYS.dashboard(period),
    queryFn: () => getAnalyticsDashboard(period),
  });
}

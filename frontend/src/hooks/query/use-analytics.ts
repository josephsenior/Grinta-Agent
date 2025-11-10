/**
 * React Query hooks for analytics
 */

import { useQuery } from "@tanstack/react-query";
import * as analyticsAPI from "#/api/analytics";
import type { AnalyticsPeriod } from "#/types/analytics";

/**
 * Fetch analytics dashboard data
 */
export function useAnalyticsDashboard(period: AnalyticsPeriod = "week") {
  return useQuery({
    queryKey: ["analytics-dashboard", period],
    queryFn: () => analyticsAPI.getAnalyticsDashboard(period),
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  });
}

/**
 * Fetch quick analytics summary
 */
export function useAnalyticsSummary(period: AnalyticsPeriod = "week") {
  return useQuery({
    queryKey: ["analytics-summary", period],
    queryFn: () => analyticsAPI.getAnalyticsSummary(period),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch model usage statistics
 */
export function useModelUsageStats(period: AnalyticsPeriod = "week") {
  return useQuery({
    queryKey: ["analytics-models", period],
    queryFn: () => analyticsAPI.getModelUsageStats(period),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * Fetch cost breakdown
 */
export function useCostBreakdown(period: AnalyticsPeriod = "week") {
  return useQuery({
    queryKey: ["analytics-costs", period],
    queryFn: () => analyticsAPI.getCostBreakdown(period),
    staleTime: 2 * 60 * 1000,
  });
}

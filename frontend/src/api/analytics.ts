/**
 * API client for analytics and usage statistics
 */

import { Forge } from "./forge-axios";
import type { AnalyticsDashboard, AnalyticsPeriod, ModelUsageStats, CostBreakdown, AnalyticsSummary } from "#/types/analytics";

/**
 * Get comprehensive analytics dashboard
 */
export async function getAnalyticsDashboard(
  period: AnalyticsPeriod = "week",
): Promise<AnalyticsDashboard> {
  const response = await Forge.get(`/api/analytics/dashboard`, {
    params: { period },
  });
  return response.data;
}

/**
 * Get quick analytics summary
 */
export async function getAnalyticsSummary(
  period: AnalyticsPeriod = "week",
): Promise<AnalyticsSummary> {
  const response = await Forge.get(`/api/analytics/summary`, {
    params: { period },
  });
  return response.data;
}

/**
 * Get usage statistics by model
 */
export async function getModelUsageStats(
  period: AnalyticsPeriod = "week",
): Promise<ModelUsageStats[]> {
  const response = await Forge.get(`/api/analytics/models`, {
    params: { period },
  });
  return response.data;
}

/**
 * Get detailed cost breakdown
 */
export async function getCostBreakdown(
  period: AnalyticsPeriod = "week",
): Promise<CostBreakdown> {
  const response = await Forge.get(`/api/analytics/costs/breakdown`, {
    params: { period },
  });
  return response.data;
}

/**
 * Export analytics data
 */
export async function exportAnalytics(
  period: AnalyticsPeriod = "week",
  format: "json" | "csv" = "json",
): Promise<{ format: string; exported_at: string; data: any }> {
  const response = await Forge.get(`/api/analytics/export`, {
    params: { period, format },
  });
  return response.data;
}



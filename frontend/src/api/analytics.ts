/**
 * API client for analytics endpoints
 */

import { Forge } from "./forge-axios";
import type {
  AnalyticsDashboard,
  AnalyticsPeriod,
  AnalyticsSummary,
  ModelUsageStats,
  CostBreakdown,
} from "#/types/analytics";

/**
 * Get the full analytics dashboard data
 */
export async function getAnalyticsDashboard(
  period: AnalyticsPeriod = "week",
): Promise<AnalyticsDashboard> {
  const response = await Forge.get<AnalyticsDashboard>("/api/analytics/dashboard", {
    params: { period },
  });
  return response.data;
}

/**
 * Get analytics summary data
 */
export async function getAnalyticsSummary(
  period: AnalyticsPeriod = "week",
): Promise<AnalyticsSummary> {
  const response = await Forge.get<AnalyticsSummary>("/api/analytics/summary", {
    params: { period },
  });
  return response.data;
}

/**
 * Get model usage statistics
 */
export async function getModelUsageStats(
  period: AnalyticsPeriod = "week",
): Promise<ModelUsageStats[]> {
  const response = await Forge.get<ModelUsageStats[]>("/api/analytics/models", {
    params: { period },
  });
  return response.data;
}

/**
 * Get cost breakdown
 */
export async function getCostBreakdown(
  period: AnalyticsPeriod = "week",
): Promise<CostBreakdown> {
  const response = await Forge.get<CostBreakdown>("/api/analytics/costs/breakdown", {
    params: { period },
  });
  return response.data;
}

/**
 * Export analytics data in the specified format
 */
export async function exportAnalytics(
  period: AnalyticsPeriod,
  format: "json" | "csv" | "pdf",
): Promise<any> {
  const response = await Forge.get("/api/analytics/export", {
    params: { period, format },
  });
  return response.data;
}

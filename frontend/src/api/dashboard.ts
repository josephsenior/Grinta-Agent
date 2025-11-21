/**
 * API client for dashboard endpoints
 */

import { Forge } from "./forge-axios";

export interface QuickStats {
  total_conversations: number;
  active_conversations: number;
  total_cost: number;
  success_rate: number;
}

export interface RecentConversation {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  cost?: number;
  repository?: string;
}

export interface ActivityItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface DashboardStats {
  quick_stats: QuickStats;
  recent_conversations: RecentConversation[];
  activity_feed: ActivityItem[];
}

export interface DashboardStatsResponse {
  status: string;
  data: DashboardStats;
}

/**
 * Get dashboard statistics including quick stats, recent conversations, and activity feed
 */
export async function getDashboardStats(
  recentLimit?: number,
  activityLimit?: number,
): Promise<DashboardStats> {
  const params: Record<string, number> = {};
  if (recentLimit !== undefined) {
    params.recent_limit = recentLimit;
  }
  if (activityLimit !== undefined) {
    params.activity_limit = activityLimit;
  }

  const response = await Forge.get<DashboardStatsResponse>(
    "/api/dashboard/stats",
    { params },
  );
  return response.data.data;
}

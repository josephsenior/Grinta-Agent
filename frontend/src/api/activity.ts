/**
 * API client for activity feed endpoints
 */

import { Forge } from "./forge-axios";

export interface ActivityItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface PaginatedActivities {
  data: ActivityItem[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    has_more: boolean;
    total_pages?: number;
  };
}

/**
 * Get activity feed for the current user
 */
export async function getActivityFeed(
  page: number = 1,
  limit: number = 20,
  type?: string,
): Promise<PaginatedActivities> {
  const params: Record<string, string | number> = {
    page,
    limit,
  };
  if (type) {
    params.type = type;
  }

  const response = await Forge.get<PaginatedActivities>("/api/activity", {
    params,
  });
  return response.data;
}

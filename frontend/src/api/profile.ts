/**
 * API client for profile endpoints
 */

import { Forge } from "./forge-axios";

export interface UserStatistics {
  total_conversations: number;
  active_conversations: number;
  total_cost: number;
  success_rate: number;
  total_tokens: number;
  avg_response_time: number;
}

export interface ActivityTimelineItem {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface UserProfile {
  id: string;
  username?: string;
  email?: string;
  role?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProfileData {
  user: UserProfile;
  statistics: UserStatistics;
  recent_activity: ActivityTimelineItem[];
}

export interface ProfileResponse {
  status: string;
  data: ProfileData;
}

export interface UpdateProfileRequest {
  username?: string;
  email?: string;
}

export interface UpdateProfileResponse {
  status: string;
  data: UserProfile;
  message?: string;
}

/**
 * Get user profile with statistics and activity timeline
 */
export async function getUserProfile(): Promise<ProfileData> {
  const response = await Forge.get<ProfileResponse>("/api/profile");
  return response.data.data;
}

/**
 * Update user profile
 */
export async function updateUserProfile(
  data: UpdateProfileRequest,
): Promise<UserProfile> {
  const response = await Forge.patch<UpdateProfileResponse>(
    "/api/profile",
    data,
  );
  return response.data.data;
}

/**
 * Get user statistics only
 */
export async function getUserStatistics(): Promise<UserStatistics> {
  const response = await Forge.get<{ status: string; data: UserStatistics }>(
    "/api/profile/stats",
  );
  return response.data.data;
}

/**
 * Get user activity timeline
 */
export async function getUserActivity(
  limit?: number,
  offset?: number,
): Promise<ActivityTimelineItem[]> {
  const params: Record<string, number> = {};
  if (limit !== undefined) {
    params.limit = limit;
  }
  if (offset !== undefined) {
    params.offset = offset;
  }

  const response = await Forge.get<{
    status: string;
    data: ActivityTimelineItem[];
  }>("/api/profile/activity", { params });
  return response.data.data;
}

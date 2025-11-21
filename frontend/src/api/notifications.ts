/**
 * API client for notifications endpoints
 */

import { Forge } from "./forge-axios";

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
  metadata?: Record<string, unknown>;
}

export interface PaginatedNotifications {
  data: Notification[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    has_more: boolean;
    total_pages?: number;
  };
}

export interface UnreadCountResponse {
  status: string;
  data: {
    unread_count: number;
  };
}

export interface NotificationResponse {
  status: string;
  data: Notification;
}

export interface SuccessResponse {
  status: string;
  message?: string;
}

/**
 * List notifications for the current user
 */
export async function listNotifications(
  page: number = 1,
  limit: number = 20,
  read?: boolean,
): Promise<PaginatedNotifications> {
  const params: Record<string, string | number> = {
    page,
    limit,
  };
  if (read !== undefined) {
    params.read = read.toString();
  }

  const response = await Forge.get<PaginatedNotifications>(
    "/api/notifications",
    { params },
  );
  return response.data;
}

/**
 * Get a specific notification
 */
export async function getNotification(
  notificationId: string,
): Promise<Notification> {
  const response = await Forge.get<NotificationResponse>(
    `/api/notifications/${notificationId}`,
  );
  return response.data.data;
}

/**
 * Get unread notification count
 */
export async function getUnreadCount(): Promise<number> {
  const response = await Forge.get<UnreadCountResponse>(
    "/api/notifications/unread-count",
  );
  return response.data.data.unread_count;
}

/**
 * Mark a notification as read
 */
export async function markNotificationAsRead(
  notificationId: string,
): Promise<void> {
  await Forge.patch<SuccessResponse>(
    `/api/notifications/${notificationId}/read`,
  );
}

/**
 * Mark all notifications as read
 */
export async function markAllNotificationsAsRead(): Promise<void> {
  await Forge.patch<SuccessResponse>("/api/notifications/read-all");
}

/**
 * Delete a notification
 */
export async function deleteNotification(
  notificationId: string,
): Promise<void> {
  await Forge.delete<SuccessResponse>(`/api/notifications/${notificationId}`);
}

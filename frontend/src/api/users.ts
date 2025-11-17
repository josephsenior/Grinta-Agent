import type { User } from "../types/auth";
import { Forge } from "./forge-axios";

export interface PaginatedUsersResponse {
  items: User[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
  role?: "admin" | "user" | "service";
  is_active?: boolean;
  email_verified?: boolean;
}

export const usersApi = {
  /**
   * List all users (admin only)
   */
  async listUsers(
    page: number = 1,
    limit: number = 20,
  ): Promise<PaginatedUsersResponse> {
    const response = await Forge.get<{
      status: string;
      data: PaginatedUsersResponse;
    }>("/api/users", {
      params: { page, limit },
    });
    return response.data.data;
  },

  /**
   * Get user by ID
   */
  async getUserById(userId: string): Promise<User> {
    const response = await Forge.get<{ status: string; data: { user: User } }>(
      `/api/users/${userId}`,
    );
    return response.data.data.user;
  },

  /**
   * Update user
   */
  async updateUser(userId: string, data: UpdateUserRequest): Promise<User> {
    const response = await Forge.patch<{
      status: string;
      data: { user: User };
    }>(`/api/users/${userId}`, data);
    return response.data.data.user;
  },

  /**
   * Delete user (admin only)
   */
  async deleteUser(userId: string): Promise<void> {
    await Forge.delete(`/api/users/${userId}`);
  },
};

import type {
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  User,
} from "../types/auth";
import { Forge } from "./forge-axios";

export const authApi = {
  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<LoginResponse> {
    const response = await Forge.post<{
      status: string;
      data: LoginResponse;
      message: string;
    }>("/api/auth/register", data);
    return response.data.data;
  },

  /**
   * Login user
   */
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await Forge.post<{
      status: string;
      data: LoginResponse;
      message: string;
    }>("/api/auth/login", data);
    return response.data.data;
  },

  /**
   * Logout user (client-side token discard)
   */
  async logout(): Promise<void> {
    await Forge.post("/api/auth/logout");
  },

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    const response = await Forge.get<{ status: string; data: { user: User } }>(
      "/api/auth/me",
    );
    return response.data.data.user;
  },

  /**
   * Refresh authentication token
   */
  async refreshToken(): Promise<{ token: string; expires_in: number }> {
    const response = await Forge.post<{
      status: string;
      data: { token: string; expires_in: number };
    }>("/api/auth/refresh");
    return response.data.data;
  },

  /**
   * Change password
   */
  async changePassword(data: ChangePasswordRequest): Promise<void> {
    await Forge.post("/api/auth/change-password", data);
  },

  /**
   * Request password reset
   */
  async forgotPassword(data: ForgotPasswordRequest): Promise<void> {
    await Forge.post("/api/auth/forgot-password", data);
  },

  /**
   * Reset password with token
   */
  async resetPassword(data: ResetPasswordRequest): Promise<void> {
    await Forge.post("/api/auth/reset-password", data);
  },

  /**
   * Get OAuth authorization URL
   */
  async getOAuthUrl(
    provider: "github" | "google",
    redirectUri?: string,
  ): Promise<string> {
    const params = redirectUri
      ? `?redirect_uri=${encodeURIComponent(redirectUri)}`
      : "";
    const response = await Forge.get<{
      status: string;
      data: { auth_url: string; state: string };
    }>(`/api/auth/oauth/${provider}/authorize${params}`);
    return response.data.data.auth_url;
  },
};

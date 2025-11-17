export interface User {
  id: string;
  email: string;
  username: string;
  role: "admin" | "user" | "service";
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  email: string;
  reset_token: string;
  new_password: string;
}

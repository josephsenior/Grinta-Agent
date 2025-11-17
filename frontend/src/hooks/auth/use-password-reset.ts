import { useMutation } from "@tanstack/react-query";
import { authApi } from "../../api/auth";
import type {
  ForgotPasswordRequest,
  ResetPasswordRequest,
} from "../../types/auth";

export function useForgotPassword() {
  return useMutation({
    mutationFn: (data: ForgotPasswordRequest) => authApi.forgotPassword(data),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (data: ResetPasswordRequest) => authApi.resetPassword(data),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      authApi.changePassword(data),
  });
}

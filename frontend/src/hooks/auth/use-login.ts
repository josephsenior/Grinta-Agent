import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../../context/auth-context";
import type { LoginRequest } from "../../types/auth";

export function useLogin() {
  const { login } = useAuth();

  return useMutation({
    mutationFn: (credentials: LoginRequest) => login(credentials),
  });
}

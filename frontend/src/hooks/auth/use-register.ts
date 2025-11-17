import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../../context/auth-context";
import type { RegisterRequest } from "../../types/auth";

export function useRegister() {
  const { register } = useAuth();

  return useMutation({
    mutationFn: (data: RegisterRequest) => register(data),
  });
}

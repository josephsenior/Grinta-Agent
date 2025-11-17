import { useQuery } from "@tanstack/react-query";
import { authApi } from "../../api/auth";
import { useAuth } from "../../context/auth-context";

export function useUserProfile() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: ["user", "profile"],
    queryFn: () => authApi.getCurrentUser(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

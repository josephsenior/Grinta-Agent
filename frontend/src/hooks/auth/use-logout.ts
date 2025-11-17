import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import posthog from "posthog-js";
import { useAuth } from "../../context/auth-context";

export function useLogout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await logout();
      // Clear all queries
      queryClient.removeQueries({ queryKey: ["tasks"] });
      queryClient.removeQueries({ queryKey: ["settings"] });
      queryClient.removeQueries({ queryKey: ["user"] });
      queryClient.removeQueries({ queryKey: ["users"] });
      queryClient.removeQueries({ queryKey: ["secrets"] });

      // Reset PostHog
      if (typeof posthog !== "undefined") {
        posthog.reset();
      }

      // Navigate to login
      navigate("/auth/login");
    },
  });
}

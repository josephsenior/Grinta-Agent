import { useQuery } from "@tanstack/react-query";

export interface SubscriptionAccess {
  status: "ACTIVE" | "INACTIVE" | "FREE";
  tier: "FREE" | "PRO" | "ENTERPRISE";
}

export function useSubscriptionAccess() {
  return useQuery<SubscriptionAccess>({
    queryKey: ["subscription-access"],
    queryFn: async () => {
      // Mock implementation - in a real app this would call an API
      return {
        status: "FREE",
        tier: "FREE",
      };
    },
  });
}

import { useQuery } from "@tanstack/react-query";
import { getFeatureFlags, type FeatureFlagsResponse } from "#/api/features";

export const useFeatureFlags = () =>
  useQuery<FeatureFlagsResponse>({
    queryKey: ["feature-flags"],
    queryFn: async () => getFeatureFlags(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
  });

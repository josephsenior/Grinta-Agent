import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getUserProfile,
  updateUserProfile,
  getUserStatistics,
  getUserActivity,
  type UpdateProfileRequest,
} from "#/api/profile";

export const useUserProfile = () => {
  return useQuery({
    queryKey: ["user", "profile"],
    queryFn: getUserProfile,
    enabled: true,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useUserStatistics = () => {
  return useQuery({
    queryKey: ["user", "statistics"],
    queryFn: getUserStatistics,
    enabled: true,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUserActivity = (limit?: number, offset?: number) => {
  return useQuery({
    queryKey: ["user", "activity", limit, offset],
    queryFn: () => getUserActivity(limit, offset),
    enabled: true,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
};

export const useUpdateProfile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateProfileRequest) => updateUserProfile(data),
    onSuccess: () => {
      // Invalidate profile-related queries
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
      queryClient.invalidateQueries({ queryKey: ["user", "statistics"] });
    },
  });
};

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getUserProfile,
  updateUserProfile,
  getUserStatistics,
  getUserActivity,
  type UpdateProfileRequest,
} from "#/api/profile";
import { useIsAuthed } from "./use-is-authed";

export const useUserProfile = () => {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: ["user", "profile"],
    queryFn: getUserProfile,
    enabled: !!userIsAuthenticated,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useUserStatistics = () => {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: ["user", "statistics"],
    queryFn: getUserStatistics,
    enabled: !!userIsAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUserActivity = (limit?: number, offset?: number) => {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: ["user", "activity", limit, offset],
    queryFn: () => getUserActivity(limit, offset),
    enabled: !!userIsAuthenticated,
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

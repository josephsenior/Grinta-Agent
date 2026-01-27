import { useQuery } from "@tanstack/react-query";
import { getUserProfile } from "#/api/profile";

/**
 * Hook to check if the user is authenticated.
 * It attempts to fetch the user profile and returns true if successful.
 */
export const useIsAuthed = () => {
  return useQuery({
    queryKey: ["is-authed"],
    queryFn: async () => {
      try {
        await getUserProfile();
        return true;
      } catch (err) {
        return false;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: false,
  });
};

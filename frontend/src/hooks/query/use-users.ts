import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usersApi } from "../../api/users";
import type { UpdateUserRequest } from "../../api/users";

export function useUsers(page: number = 1, limit: number = 20) {
  return useQuery({
    queryKey: ["users", page, limit],
    queryFn: () => usersApi.listUsers(page, limit),
  });
}

export function useUser(userId: string) {
  return useQuery({
    queryKey: ["user", userId],
    queryFn: () => usersApi.getUserById(userId),
    enabled: !!userId,
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      data,
    }: {
      userId: string;
      data: UpdateUserRequest;
    }) => usersApi.updateUser(userId, data),
    onSuccess: (updatedUser) => {
      // Invalidate user queries
      queryClient.invalidateQueries({ queryKey: ["user", updatedUser.id] });
      queryClient.invalidateQueries({ queryKey: ["users"] });
      // Also invalidate current user profile if it's the same user
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => usersApi.deleteUser(userId),
    onSuccess: () => {
      // Invalidate users list
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}

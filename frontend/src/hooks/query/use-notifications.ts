import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from "@tanstack/react-query";
import {
  listNotifications,
  getNotification,
  getUnreadCount,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteNotification,
} from "#/api/notifications";

export const useNotifications = (
  page: number = 1,
  limit: number = 20,
  read?: boolean,
) => {
  return useQuery({
    queryKey: ["notifications", page, limit, read],
    queryFn: () => listNotifications(page, limit, read),
    enabled: true,
    staleTime: 30 * 1000, // 30 seconds
  });
};

export const useInfiniteNotifications = (
  limit: number = 20,
  read?: boolean,
) => {
  return useInfiniteQuery({
    queryKey: ["notifications", "infinite", limit, read],
    queryFn: ({ pageParam = 1 }) => listNotifications(pageParam, limit, read),
    enabled: true,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination.has_more) {
        return lastPage.pagination.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 30 * 1000, // 30 seconds
  });
};

export const useNotification = (notificationId: string) => {
  return useQuery({
    queryKey: ["notifications", notificationId],
    queryFn: () => getNotification(notificationId),
    enabled: !!notificationId,
  });
};

export const useUnreadCount = () => {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: getUnreadCount,
    enabled: true,
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
    staleTime: 10 * 1000, // 10 seconds
  });
};

export const useMarkNotificationAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: markNotificationAsRead,
    onSuccess: () => {
      // Invalidate notifications queries
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
};

export const useMarkAllNotificationsAsRead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: markAllNotificationsAsRead,
    onSuccess: () => {
      // Invalidate notifications queries
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
};

export const useDeleteNotification = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteNotification,
    onSuccess: () => {
      // Invalidate notifications queries
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
};

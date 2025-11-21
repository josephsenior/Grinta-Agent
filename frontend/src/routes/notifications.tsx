import React from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  Check,
  X,
  AlertCircle,
  Info,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import {
  useInfiniteNotifications,
  useMarkNotificationAsRead,
  useMarkAllNotificationsAsRead,
  useDeleteNotification,
  useUnreadCount,
} from "#/hooks/query/use-notifications";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";

/**
 * Notification Icon Component
 */
function NotificationIcon({ type }: { type: string }) {
  switch (type.toLowerCase()) {
    case "success":
    case "conversation_complete":
      return <CheckCircle className="h-5 w-5 text-[#10B981]" />;
    case "warning":
    case "conversation_warning":
      return <AlertCircle className="h-5 w-5 text-[#F59E0B]" />;
    case "error":
    case "conversation_error":
      return <XCircle className="h-5 w-5 text-[#EF4444]" />;
    case "info":
    case "conversation_created":
    case "conversation_updated":
    default:
      return <Info className="h-5 w-5 text-[#3B82F6]" />;
  }
}

/**
 * Notifications Page
 * Matches design system specifications
 */
export default function NotificationsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    data: notificationsData,
    isLoading: notificationsLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteNotifications(20);
  const { data: unreadCount = 0 } = useUnreadCount();
  const markAsReadMutation = useMarkNotificationAsRead();
  const markAllAsReadMutation = useMarkAllNotificationsAsRead();
  const deleteNotificationMutation = useDeleteNotification();

  const notifications = React.useMemo(
    () => notificationsData?.pages.flatMap((page) => page.data) ?? [],
    [notificationsData],
  );

  // Precompute unread message to avoid nested ternaries in JSX
  let unreadMessage: string | null = null;
  if (unreadCount > 0) {
    const plural = unreadCount > 1 ? "s" : "";
    unreadMessage = t(
      "NOTIFICATIONS$UNREAD_MESSAGE",
      `You have ${unreadCount} unread notification${plural}`,
    );
  } else {
    unreadMessage = t("NOTIFICATIONS$ALL_CAUGHT_UP", "You're all caught up!");
  }

  const handleMarkAsRead = (notificationId: string) => {
    markAsReadMutation.mutate(notificationId);
  };

  const handleMarkAllAsRead = () => {
    markAllAsReadMutation.mutate();
  };

  const handleDelete = (notificationId: string) => {
    deleteNotificationMutation.mutate(notificationId);
  };

  // Precompute notifications section to avoid nested ternary expressions
  let notificationsSection: React.ReactNode = null;
  if (notificationsLoading) {
    notificationsSection = (
      <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
        <div className="flex items-center justify-center">
          <LoadingSpinner size="medium" />
        </div>
      </Card>
    );
  } else if (notifications.length === 0) {
    notificationsSection = (
      <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
        <Bell className="h-16 w-16 text-[#94A3B8] opacity-50 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-[#FFFFFF] mb-2">
          {t("COMMON$NO_NOTIFICATIONS", { defaultValue: "No notifications" })}
        </h3>
        <p className="text-sm text-[#94A3B8]">
          {t("COMMON$NO_NOTIFICATIONS_DESCRIPTION", {
            defaultValue:
              "You'll see notifications here when you receive them.",
          })}
        </p>
      </Card>
    );
  } else {
    notificationsSection = (
      <div className="space-y-3">
        {notifications.map((notification) => (
          <Card
            key={notification.id}
            className={cn(
              "bg-[#000000] border rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)] transition-all duration-200",
              notification.read
                ? "border-[#1a1a1a]"
                : "border-[rgba(139,92,246,0.1)] bg-[rgba(139,92,246,0.05)]",
            )}
          >
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 mt-0.5">
                <NotificationIcon type={notification.type} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex-1">
                    <h4 className="text-base font-semibold text-[#FFFFFF] mb-1">
                      {notification.title}
                    </h4>
                    <p className="text-sm text-[#94A3B8]">
                      {notification.message}
                    </p>
                  </div>
                  {!notification.read && (
                    <div className="w-2 h-2 rounded-full bg-[#8b5cf6] flex-shrink-0 mt-2" />
                  )}
                </div>
                <div className="flex items-center justify-between mt-4">
                  <span className="text-xs text-[#94A3B8]">
                    <ClientFormattedDate iso={notification.created_at} />
                  </span>
                  <div className="flex items-center gap-2">
                    {!notification.read && (
                      <button
                        type="button"
                        onClick={() => handleMarkAsRead(notification.id)}
                        disabled={markAsReadMutation.isPending}
                        className="px-3 py-1.5 rounded-lg border border-[#1a1a1a] bg-[#000000] hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] text-xs text-[#94A3B8] hover:text-[#FFFFFF] transition-colors disabled:opacity-50"
                      >
                        <Check className="h-3 w-3 inline mr-1" />
                        {t("NOTIFICATIONS$MARK_READ", "Mark Read")}
                      </button>
                    )}
                    {notification.action_url && (
                      <button
                        type="button"
                        onClick={() => navigate(notification.action_url!)}
                        className="px-3 py-1.5 rounded-lg border border-[#8b5cf6] bg-[rgba(139,92,246,0.1)] hover:bg-[rgba(139,92,246,0.15)] text-xs text-[#FFFFFF] font-medium transition-colors"
                      >
                        {t("NOTIFICATIONS$VIEW", "View")}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(notification.id)}
                      disabled={deleteNotificationMutation.isPending}
                      className="p-1.5 rounded-lg border border-[#1a1a1a] bg-[#000000] hover:bg-[rgba(239,68,68,0.1)] hover:border-[#EF4444] text-[#94A3B8] hover:text-[#EF4444] transition-colors disabled:opacity-50"
                      aria-label="Delete notification"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
        {hasNextPage && (
          <div className="flex justify-center pt-4">
            <Button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-6 py-3 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150"
            >
              {isFetchingNextPage
                ? t("COMMON$LOADING", "Loading...")
                : t("NOTIFICATIONS$LOAD_MORE", "Load More")}
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <AuthGuard>
      <AppLayout>
        <div className="space-y-8">
          {/* Page Title */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
                {t("NOTIFICATIONS$TITLE", "Notifications")}
              </h1>
              <p className="text-sm text-[#94A3B8]">{unreadMessage}</p>
            </div>
            <div className="flex items-center gap-3">
              {unreadCount > 0 && (
                <Button
                  onClick={handleMarkAllAsRead}
                  disabled={markAllAsReadMutation.isPending}
                  className="bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg px-6 py-3 hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6] transition-all duration-150"
                >
                  <Check className="mr-2 h-4 w-4" />
                  {t("NOTIFICATIONS$MARK_ALL_READ", "Mark All Read")}
                </Button>
              )}
            </div>
          </div>

          {/* Notification List */}
          {notificationsSection}
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

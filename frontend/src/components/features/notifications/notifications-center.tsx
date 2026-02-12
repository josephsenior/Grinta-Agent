import React, { useState, useRef, useEffect } from "react";
import { Bell, Check, X, AlertCircle, Info, CheckCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { cn } from "#/utils/utils";
import type { Notification } from "#/api/notifications";
import {
  useNotifications,
  useUnreadCount,
  useMarkNotificationAsRead,
  useMarkAllNotificationsAsRead,
  useDeleteNotification,
} from "#/hooks/query/use-notifications";

export function NotificationsCenter() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { data: notificationsData } = useNotifications(1, 20);
  const { data: unreadCount = 0 } = useUnreadCount();
  const markAsReadMutation = useMarkNotificationAsRead();
  const markAllAsReadMutation = useMarkAllNotificationsAsRead();
  const deleteMutation = useDeleteNotification();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const notifications: Notification[] = notificationsData?.data ?? [];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
      return undefined;
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }

    return undefined;
  }, [isOpen]);

  const getIcon = (type: string) => {
    switch (type) {
      case "success":
        return CheckCircle;
      case "warning":
        return AlertCircle;
      case "error":
        return AlertCircle;
      default:
        return Info;
    }
  };

  const getIconColor = (type: string) => {
    switch (type) {
      case "success":
        return "text-success-400";
      case "warning":
        return "text-yellow-400";
      case "error":
        return "text-danger-400";
      default:
        return "text-brand-400";
    }
  };

  const formatTimestamp = (dateStr: string) => {
    const now = Date.now();
    const diff = now - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative p-2 rounded-lg transition-all duration-200 text-white/70 hover:text-white hover:bg-white/10",
          isOpen && "text-white bg-white/10",
        )}
        aria-label="Notifications"
        aria-expanded={isOpen}
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-danger-500 text-white text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 rounded-xl border border-white/10 bg-black/90 backdrop-blur-xl shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">
              {t(I18nKey.NOTIFICATIONS$TITLE)}
            </h3>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => {
                  markAllAsReadMutation.mutate();
                }}
                className="text-xs text-white/60 hover:text-white transition-colors"
              >
                {t(I18nKey.NOTIFICATIONS$MARK_ALL_READ)}
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <Bell className="h-8 w-8 text-white/20 mx-auto mb-2" />
                <p className="text-sm text-white/60">
                  {t(I18nKey.NOTIFICATIONS$NO_NOTIFICATIONS)}
                </p>
              </div>
            ) : (
              <div className="py-2">
                {notifications.map((notification) => {
                  const Icon = getIcon(notification.type);
                  return (
                    <div
                      key={notification.id}
                      className={cn(
                        "px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors",
                        !notification.read && "bg-white/5",
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={cn(
                            "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                            getIconColor(notification.type),
                            "bg-white/5",
                          )}
                        >
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <p className="text-sm font-medium text-white">
                              {notification.title}
                            </p>
                            {!notification.read && (
                              <div className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0 mt-1.5" />
                            )}
                          </div>
                          <p className="text-xs text-white/60 mb-2">
                            {notification.message}
                          </p>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-white/40">
                              {formatTimestamp(notification.created_at)}
                            </span>
                            <div className="flex items-center gap-2">
                              {notification.action_url && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    navigate(notification.action_url!);
                                    setIsOpen(false);
                                  }}
                                  className="text-xs text-brand-400 hover:text-brand-300 font-medium"
                                >
                                  View
                                </button>
                              )}
                              {!notification.read && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    markAsReadMutation.mutate(notification.id)
                                  }
                                  className="p-1 rounded hover:bg-white/10 transition-colors"
                                  aria-label="Mark as read"
                                >
                                  <Check className="h-3 w-3 text-white/60" />
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() =>
                                  deleteMutation.mutate(notification.id)
                                }
                                className="p-1 rounded hover:bg-white/10 transition-colors"
                                aria-label="Dismiss"
                              >
                                <X className="h-3 w-3 text-white/60" />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-3 border-t border-white/10">
              <button
                type="button"
                onClick={() => {
                  navigate("/notifications");
                  setIsOpen(false);
                }}
                className="w-full text-center text-sm text-brand-400 hover:text-brand-300 font-medium transition-colors"
              >
                {t("COMMON$VIEW_ALL", {
                  defaultValue: "View All Notifications",
                })}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

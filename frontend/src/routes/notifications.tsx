import React from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import {
  Bell,
  Check,
  X,
  AlertCircle,
  Info,
  CheckCircle,
  XCircle,
  Trash2,
  ArrowLeft,
} from "lucide-react";
import AnimatedBackground from "#/components/landing/AnimatedBackground";
import { PageHero } from "#/components/layout/PageHero";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import type { RootState } from "#/store";
import {
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearAll,
  type Notification,
} from "#/store/notifications-slice";
import { AppLayout } from "#/components/layout/AppLayout";

export default function NotificationsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const notifications = useSelector(
    (state: RootState) => state.notifications.notifications,
  );

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: Notification["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle className="h-5 w-5 text-accent-emerald" />;
      case "warning":
        return <AlertCircle className="h-5 w-5 text-warning-500" />;
      case "error":
        return <XCircle className="h-5 w-5 text-danger-500" />;
      case "info":
      default:
        return <Info className="h-5 w-5 text-brand-500" />;
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
      <div aria-hidden className="pointer-events-none">
        <AnimatedBackground />
      </div>
      <AppLayout>
        <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 sm:p-8 lg:p-10">
          <PageHero
            eyebrow={t("COMMON$NOTIFICATIONS", {
              defaultValue: "Notifications",
            })}
            title={t("COMMON$YOUR_NOTIFICATIONS", {
              defaultValue: "Your Notifications",
            })}
            description={
              unreadCount > 0
                ? t("COMMON$UNREAD_NOTIFICATIONS", {
                    defaultValue: `You have ${unreadCount} unread notification${unreadCount > 1 ? "s" : ""}`,
                  })
                : t("COMMON$ALL_CAUGHT_UP", {
                    defaultValue: "You're all caught up!",
                  })
            }
            align="left"
            actions={
              <div className="flex items-center gap-3">
                {unreadCount > 0 && (
                  <Button
                    onClick={() => dispatch(markAllAsRead())}
                    variant="outline"
                    className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                  >
                    <Check className="mr-2 h-4 w-4" />
                    Mark All Read
                  </Button>
                )}
                {notifications.length > 0 && (
                  <Button
                    onClick={() => dispatch(clearAll())}
                    variant="outline"
                    className="border border-red-500/20 bg-transparent text-red-400 hover:bg-red-500/10 font-semibold rounded-xl px-6 py-3"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Clear All
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => navigate("/")}
                  className="border border-white/20 bg-transparent text-foreground hover:bg-white/10 font-semibold rounded-xl px-6 py-3"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Home
                </Button>
              </div>
            }
          />

          {notifications.length === 0 ? (
            <Card className="p-12 text-center">
              <Bell className="h-16 w-16 text-white/20 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                {t("COMMON$NO_NOTIFICATIONS", {
                  defaultValue: "No notifications",
                })}
              </h3>
              <p className="text-white/60">
                {t("COMMON$NO_NOTIFICATIONS_DESCRIPTION", {
                  defaultValue:
                    "You'll see notifications here when you receive them.",
                })}
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {notifications.map((notification) => (
                <Card
                  key={notification.id}
                  className={cn(
                    "p-5 transition-all",
                    !notification.read && "border-white/20 bg-white/5",
                  )}
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 mt-0.5">
                      {getIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex-1">
                          <h4 className="text-base font-semibold text-white mb-1">
                            {notification.title}
                          </h4>
                          <p className="text-sm text-white/70">
                            {notification.message}
                          </p>
                        </div>
                        {!notification.read && (
                          <div className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0 mt-2" />
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-3">
                        <span className="text-xs text-white/50">
                          {formatTimestamp(notification.timestamp)}
                        </span>
                        <div className="flex items-center gap-2">
                          {!notification.read && (
                            <button
                              onClick={() =>
                                dispatch(markAsRead(notification.id))
                              }
                              className="px-3 py-1.5 rounded-lg border border-white/10 bg-black/60 hover:bg-white/5 text-xs text-white/70 hover:text-white transition-colors"
                            >
                              <Check className="h-3 w-3 inline mr-1" />
                              Mark Read
                            </button>
                          )}
                          {notification.action && (
                            <button
                              onClick={notification.action.onClick}
                              className="px-3 py-1.5 rounded-lg border border-white/20 bg-white/10 hover:bg-white/15 text-xs text-white font-medium transition-colors"
                            >
                              {notification.action.label}
                            </button>
                          )}
                          <button
                            onClick={() =>
                              dispatch(removeNotification(notification.id))
                            }
                            className="p-1.5 rounded-lg border border-white/10 bg-black/60 hover:bg-white/5 text-white/50 hover:text-white transition-colors"
                            aria-label="Dismiss"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </AppLayout>
    </main>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;

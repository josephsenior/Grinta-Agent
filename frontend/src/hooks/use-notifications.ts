import { useDispatch } from "react-redux";
import { useCallback } from "react";
import {
  addNotification,
  type Notification,
} from "#/store/notifications-slice";

/**
 * Hook to easily add notifications from anywhere in the app
 *
 * @example
 * const { notify } = useNotifications();
 * notify({
 *   type: "success",
 *   title: "Task completed",
 *   message: "Your conversation has been saved",
 * });
 */
export function useNotifications() {
  const dispatch = useDispatch();

  const notify = useCallback(
    (notification: Omit<Notification, "id" | "timestamp" | "read">) => {
      dispatch(addNotification(notification));
    },
    [dispatch],
  );

  const notifySuccess = useCallback(
    (title: string, message?: string, action?: Notification["action"]) => {
      notify({ type: "success", title, message: message || "", action });
    },
    [notify],
  );

  const notifyError = useCallback(
    (title: string, message?: string, action?: Notification["action"]) => {
      notify({ type: "error", title, message: message || "", action });
    },
    [notify],
  );

  const notifyWarning = useCallback(
    (title: string, message?: string, action?: Notification["action"]) => {
      notify({ type: "warning", title, message: message || "", action });
    },
    [notify],
  );

  const notifyInfo = useCallback(
    (title: string, message?: string, action?: Notification["action"]) => {
      notify({ type: "info", title, message: message || "", action });
    },
    [notify],
  );

  return {
    notify,
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
  };
}

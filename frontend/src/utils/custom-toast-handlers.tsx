import { CSSProperties } from "react";
import type { ToastOptions } from "react-hot-toast";
import safeToast from "#/utils/safe-hot-toast";
import { calculateToastDuration } from "./toast-duration";
import { normalizeToastMessage } from "./toast-normalize";
import { extractUserFriendlyError, formatClientError } from "./format-error";
import type { UserFriendlyErrorData } from "#/components/shared/error/user-friendly-error";

const TOAST_STYLE: CSSProperties = {
  background: "#454545",
  border: "1px solid #717888",
  color: "#fff",
  borderRadius: "4px",
};

export const TOAST_OPTIONS: ToastOptions = {
  position: "top-right",
  style: TOAST_STYLE,
};

/**
 * Display error toast with user-friendly formatting
 */
export const displayErrorToast = (error: unknown) => {
  const showSimpleToast = (text: string, baseDuration = 4000) => {
    const normalized = normalizeToastMessage(text);
    const duration = calculateToastDuration(normalized, baseDuration);
    safeToast.error(normalized, {
      ...TOAST_OPTIONS,
      duration,
    });
  };

  if (error === null || typeof error === "undefined") {
    showSimpleToast("An unexpected error occurred");
    return;
  }

  if (
    typeof error === "string" ||
    typeof error === "number" ||
    typeof error === "boolean"
  ) {
    showSimpleToast(String(error));
    return;
  }

  // Try to extract user-friendly error from backend
  const userFriendlyError = extractUserFriendlyError(error);

  if (userFriendlyError) {
    // Use formatted error from backend
    const message = `${userFriendlyError.icon || "❌"} ${userFriendlyError.title}\n\n${userFriendlyError.suggestion || userFriendlyError.message.split("\n\n")[0]}`;
    const duration = calculateToastDuration(message, 5000);

    safeToast.error(message, {
      ...TOAST_OPTIONS,
      duration,
      icon: userFriendlyError.icon,
    });
  } else {
    // Fallback to client-side formatting
    const formatted = formatClientError(error);
    const fallbackMessage = formatted.message || formatted.title;
    const iconPrefix = formatted.icon ? `${formatted.icon} ` : "";
    const suffix = formatted.suggestion ? `\n${formatted.suggestion}` : "";
    const composedMessage = `${iconPrefix}${fallbackMessage}${suffix}`.trim();

    showSimpleToast(composedMessage, 4000);
  }
};

export const displaySuccessToast = (message: unknown) => {
  const text = normalizeToastMessage(message);
  const duration = calculateToastDuration(text, 5000);
  safeToast.success(text, { ...TOAST_OPTIONS, duration });
};

/**
 * Display user-friendly error in a detailed toast
 *
 * Shows full error with actions when available
 */
export const displayDetailedErrorToast = (
  error: UserFriendlyErrorData,
  onAction?: (action: any) => void,
) => {
  const message = `${error.icon || "❌"} ${error.title}\n\n${error.message}`;
  const duration = calculateToastDuration(message, 8000); // Longer for detailed errors

  safeToast.error(message, {
    ...TOAST_OPTIONS,
    duration,
    icon: error.icon,
  });
};

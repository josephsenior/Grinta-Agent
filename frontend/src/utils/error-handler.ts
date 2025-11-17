import posthog from "posthog-js";
import { handleStatusMessage } from "#/services/actions";
import {
  displayErrorToast,
  displayDetailedErrorToast,
} from "./custom-toast-handlers";
import { extractUserFriendlyError, formatClientError } from "./format-error";
import type { ErrorAction } from "#/components/shared/error/user-friendly-error";

interface ErrorDetails {
  message: string;
  source?: string;
  metadata?: Record<string, unknown>;
  msgId?: string;
  rawError?: unknown; // Raw error object for formatting
}

export function trackError({
  message,
  source,
  metadata = {},
  rawError,
}: ErrorDetails) {
  const error = rawError instanceof Error ? rawError : new Error(message);

  // Extract user-friendly error for better tracking
  const userFriendlyError = rawError
    ? extractUserFriendlyError(rawError)
    : null;

  posthog.captureException(error, {
    error_source: source || "unknown",
    error_category: userFriendlyError?.category || "unknown",
    error_severity: userFriendlyError?.severity || "error",
    error_code: userFriendlyError?.error_code,
    ...metadata,
  });
}

export function showErrorToast({
  message,
  source,
  metadata = {},
  rawError,
}: ErrorDetails) {
  trackError({ message, source, metadata, rawError });

  // Use raw error for formatting if available
  if (rawError) {
    displayErrorToast(rawError);
  } else {
    displayErrorToast(message);
  }
}

export function showChatError({
  message,
  source,
  metadata = {},
  msgId,
  rawError,
}: ErrorDetails) {
  trackError({ message, source, metadata, rawError });

  // Try to get user-friendly error
  const userFriendlyError = rawError
    ? extractUserFriendlyError(rawError)
    : null;

  const displayMessage = userFriendlyError
    ? `${userFriendlyError.icon || "❌"} ${userFriendlyError.title}: ${userFriendlyError.message.split("\n\n")[0]}`
    : message;

  handleStatusMessage({
    type: "error",
    message: displayMessage,
    id: msgId,
    status_update: true,
  });
}

/**
 * Show detailed error with actions
 */
export function showDetailedError(
  error: unknown,
  onAction?: (action: ErrorAction) => void,
) {
  const userFriendlyError =
    extractUserFriendlyError(error) || formatClientError(error);

  trackError({
    message: userFriendlyError.title,
    source: "detailed_error",
    metadata: { error_code: userFriendlyError.error_code },
    rawError: error,
  });

  displayDetailedErrorToast(userFriendlyError, onAction);
}

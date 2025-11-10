/**
 * Error Formatting Utilities for Frontend
 *
 * Provides client-side error formatting and handling.
 * Works with backend error formatter for consistent UX.
 */

import type { UserFriendlyErrorData } from "#/components/shared/error/user-friendly-error";

/**
 * Check if error response has user-friendly format
 */
export function isUserFriendlyError(
  error: unknown,
): error is UserFriendlyErrorData {
  return (
    typeof error === "object" &&
    error !== null &&
    "title" in error &&
    "message" in error &&
    "severity" in error
  );
}

/**
 * Extract user-friendly error from API response
 */
export function extractUserFriendlyError(
  error: unknown,
): UserFriendlyErrorData | null {
  // Check if it's already formatted
  if (isUserFriendlyError(error)) {
    return error;
  }

  // Check if it's an Axios error with formatted response
  if (typeof error === "object" && error !== null) {
    const errRec = error as Record<string, unknown>;
    const resp =
      "response" in errRec &&
      typeof errRec.response === "object" &&
      errRec.response !== null
        ? (errRec.response as Record<string, unknown>)
        : undefined;
    if (resp && "data" in resp) {
      const data = resp.data as unknown;
      if (isUserFriendlyError(data)) {
        return data;
      }
    }
  }

  return null;
}

/**
 * Format raw error into user-friendly format (client-side fallback)
 */
export function formatClientError(error: unknown): UserFriendlyErrorData {
  // Try to extract backend formatted error
  const backendError = extractUserFriendlyError(error);
  if (backendError) {
    return backendError;
  }

  const axiosDetails = extractAxiosDetails(error);
  if (axiosDetails) {
    const mapped = mapHttpStatusToError(
      axiosDetails.status,
      axiosDetails.message,
    );
    if (mapped) {
      return mapped;
    }
    return buildDefaultAxiosError(axiosDetails.message);
  }

  // Handle Error objects
  if (error instanceof Error) {
    return formatJavaScriptError(error);
  }

  // Fallback for unknown errors
  return {
    title: "Unexpected error",
    message: "Something unexpected happened. Please try refreshing the page.",
    severity: "error",
    category: "system",
    icon: "❌",
    suggestion: "Refresh the page",
    actions: [{ label: "Refresh", type: "refresh", highlight: true }],
    technical_details: String(error),
    can_retry: true,
  };
}

/**
 * Format JavaScript Error objects
 */
function formatJavaScriptError(error: Error): UserFriendlyErrorData {
  const message = error.message.toLowerCase();

  // Network errors
  if (message.includes("network") || message.includes("fetch")) {
    return {
      title: "Connection problem",
      message:
        "Can't reach the server. Check your internet connection and try again.",
      severity: "error",
      category: "network",
      icon: "📡",
      suggestion: "Check your connection",
      actions: [{ label: "Retry", type: "retry", highlight: true }],
      technical_details: error.stack,
      can_retry: true,
      retry_delay: 5,
    };
  }

  // Runtime container errors
  if (message.includes("runtime") || message.includes("container")) {
    return {
      title: "Workspace not ready",
      message:
        "Your development environment is starting up. This usually takes 30-60 seconds.",
      severity: "warning",
      category: "system",
      icon: "⏳",
      suggestion: "Wait a moment and try again",
      actions: [
        { label: "Retry", type: "retry", highlight: true },
        { label: "New Session", type: "new_conversation" },
      ],
      technical_details: error.stack,
      can_retry: true,
      retry_delay: 30,
      reassurance: "Your work is safe!",
    };
  }

  // Generic error
  return {
    title: error.name || "Error",
    message: error.message || "An error occurred",
    severity: "error",
    category: "system",
    icon: "❌",
    suggestion: "Try again or refresh the page",
    actions: [
      { label: "Retry", type: "retry", highlight: true },
      { label: "Refresh", type: "refresh" },
    ],
    technical_details: error.stack,
    can_retry: true,
  };
}

function extractAxiosDetails(
  error: unknown,
): { status?: number; message?: string } | null {
  const response = extractAxiosResponse(error);
  if (!response) {
    return null;
  }

  const status =
    typeof response.status === "number" ? response.status : undefined;
  const message =
    extractAxiosMessage(response) ?? (error as Record<string, unknown>).message;

  return {
    status,
    message: typeof message === "string" ? message : undefined,
  };
}

function extractAxiosResponse(error: unknown) {
  if (!error || typeof error !== "object" || !("response" in error)) {
    return null;
  }

  const { response } = error as Record<string, unknown>;
  return typeof response === "object" && response !== null
    ? (response as Record<string, unknown>)
    : null;
}

function extractAxiosMessage(response: Record<string, unknown>) {
  const { data } = response;
  if (typeof data === "object" && data !== null && "message" in data) {
    const { message } = data as Record<string, unknown>;
    if (typeof message === "string") {
      return message;
    }
  }

  return undefined;
}

function mapHttpStatusToError(
  status: number | undefined,
  message: string | undefined,
): UserFriendlyErrorData | null {
  switch (status) {
    case 401:
      return {
        title: "Please sign in again",
        message: "Your session has expired. Please sign in to continue.",
        severity: "warning",
        category: "authentication",
        icon: "🔒",
        suggestion: "Sign in to continue",
        actions: [
          { label: "Sign In", type: "login", url: "/login", highlight: true },
        ],
        can_retry: false,
        reassurance: "Your work is saved",
      };

    case 403:
      return {
        title: "Permission denied",
        message: "You don't have permission to perform this action.",
        severity: "error",
        category: "authentication",
        icon: "🔐",
        suggestion: "Contact your administrator",
        can_retry: false,
      };

    case 404:
      return {
        title: "Not found",
        message:
          "The requested resource wasn't found. It may have been moved or deleted.",
        severity: "warning",
        category: "user_input",
        icon: "🔍",
        suggestion: "Check the URL or try searching",
        can_retry: false,
      };

    case 429:
      return {
        title: "Too many requests",
        message:
          "You're sending requests too quickly. Please wait a moment and try again.",
        severity: "warning",
        category: "rate_limit",
        icon: "⏰",
        suggestion: "Wait a moment before retrying",
        actions: [
          { label: "Retry", type: "retry", highlight: true },
          { label: "Upgrade", type: "upgrade", url: "/billing" },
        ],
        can_retry: true,
        retry_delay: 60,
      };

    case 500:
    case 502:
    case 503:
      return {
        title: "Server error",
        message: "Our servers are experiencing issues. We're working on it!",
        severity: "error",
        category: "system",
        icon: "🔧",
        suggestion: "Wait a moment and try again",
        actions: [
          { label: "Retry", type: "retry", highlight: true },
          {
            label: "Check Status",
            type: "status",
            url: "https://status.forge.ai",
          },
        ],
        can_retry: true,
        retry_delay: 30,
        reassurance: "Your work is safe - just a temporary issue",
      };

    default:
      return status === undefined ? null : buildDefaultAxiosError(message);
  }
}

function buildDefaultAxiosError(
  message: string | undefined,
): UserFriendlyErrorData {
  return {
    title: "Something went wrong",
    message: message || "An unexpected error occurred.",
    severity: "error",
    category: "system",
    icon: "❌",
    suggestion: "Try refreshing the page",
    actions: [
      { label: "Refresh", type: "refresh", highlight: true },
      { label: "Support", type: "support", url: "mailto:support@forge.ai" },
    ],
    technical_details: message,
    can_retry: true,
  };
}

/**
 * Get appropriate icon for error category
 */
export function getErrorIcon(category: string): string {
  const iconMap: Record<string, string> = {
    user_input: "📝",
    system: "🔧",
    rate_limit: "⏰",
    authentication: "🔒",
    network: "📡",
    ai_model: "🤖",
    configuration: "⚙️",
  };

  return iconMap[category] || "❌";
}

/**
 * Get helpful message for common error patterns
 */
export function getHelpfulMessage(errorMessage: string): string {
  const lowerMessage = errorMessage.toLowerCase();

  if (lowerMessage.includes("timeout")) {
    return "The request took too long. Try simplifying your task or checking your connection.";
  }

  if (
    lowerMessage.includes("unauthorized") ||
    lowerMessage.includes("authentication")
  ) {
    return "You need to sign in again. Your session may have expired.";
  }

  if (lowerMessage.includes("not found")) {
    return "The item you're looking for doesn't exist. Check the name or path.";
  }

  if (lowerMessage.includes("rate limit")) {
    return "You're making requests too quickly. Wait a moment before trying again.";
  }

  if (lowerMessage.includes("permission")) {
    return "You don't have permission for this action. Check your access rights.";
  }

  return "An error occurred. Try again or contact support if this persists.";
}

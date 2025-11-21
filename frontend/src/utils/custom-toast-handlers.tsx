import safeToast from "#/utils/safe-hot-toast";
import { calculateToastDuration } from "./toast-duration";
import { normalizeToastMessage } from "./toast-normalize";
import { extractUserFriendlyError } from "./format-error";
import type { UserFriendlyErrorData } from "#/components/shared/error/user-friendly-error";
import { TOAST_OPTIONS } from "./custom-toast-handlers/toast-config";
import {
  isNullishError,
  isPrimitiveError,
} from "./custom-toast-handlers/error-type-checkers";
import {
  showSimpleToast,
  showUserFriendlyErrorToast,
  showClientFormattedError,
} from "./custom-toast-handlers/error-formatters";

/**
 * Display error toast with user-friendly formatting
 */
export const displayErrorToast = (error: unknown) => {
  if (isNullishError(error)) {
    showSimpleToast("An unexpected error occurred");
    return;
  }

  if (isPrimitiveError(error)) {
    showSimpleToast(String(error));
    return;
  }

  const userFriendlyError = extractUserFriendlyError(error);

  if (userFriendlyError) {
    showUserFriendlyErrorToast(userFriendlyError);
  } else {
    showClientFormattedError(error);
  }
};

/**
 * Display success toast with green accent color and checkmark icon
 * Auto-dismisses after 3s as per design specification
 */
export const displaySuccessToast = (message: unknown) => {
  const text = normalizeToastMessage(message);
  // Auto-dismiss after 3s as per UI/UX design specification
  safeToast.success(text, { ...TOAST_OPTIONS, duration: 3000 });
};

/**
 * Display user-friendly error in a detailed toast
 *
 * Shows full error with actions when available
 */
export const displayDetailedErrorToast = (error: UserFriendlyErrorData) => {
  const message = `${error.icon || "❌"} ${error.title}\n\n${error.message}`;
  const duration = calculateToastDuration(message, 8000); // Longer for detailed errors

  safeToast.error(message, {
    ...TOAST_OPTIONS,
    duration,
    icon: error.icon,
  });
};

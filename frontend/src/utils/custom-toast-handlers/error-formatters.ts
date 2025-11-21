import safeToast from "#/utils/safe-hot-toast";
import { calculateToastDuration } from "../toast-duration";
import { normalizeToastMessage } from "../toast-normalize";
import { extractUserFriendlyError, formatClientError } from "../format-error";
import { TOAST_OPTIONS } from "./toast-config";

export function showSimpleToast(text: string, baseDuration = 4000): void {
  const normalized = normalizeToastMessage(text);
  const duration = calculateToastDuration(normalized, baseDuration);
  safeToast.error(normalized, {
    ...TOAST_OPTIONS,
    duration,
  });
}

export function showUserFriendlyErrorToast(
  userFriendlyError: ReturnType<typeof extractUserFriendlyError>,
): void {
  if (!userFriendlyError) return;

  const message = `${userFriendlyError.icon || "❌"} ${userFriendlyError.title}\n\n${userFriendlyError.suggestion || userFriendlyError.message.split("\n\n")[0]}`;
  const duration = calculateToastDuration(message, 5000);

  safeToast.error(message, {
    ...TOAST_OPTIONS,
    duration,
    icon: userFriendlyError.icon,
  });
}

export function showClientFormattedError(error: unknown): void {
  const formatted = formatClientError(error);
  const fallbackMessage = formatted.message || formatted.title;
  const iconPrefix = formatted.icon ? `${formatted.icon} ` : "";
  const suffix = formatted.suggestion ? `\n${formatted.suggestion}` : "";
  const composedMessage = `${iconPrefix}${fallbackMessage}${suffix}`.trim();

  showSimpleToast(composedMessage, 4000);
}

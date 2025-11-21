/**
 * Sentry error tracking initialization and utilities.
 *
 * This module initializes Sentry for error tracking in production.
 * Set SENTRY_DSN environment variable to enable.
 */

let sentryInitialized = false;

export async function initSentry(): Promise<void> {
  // Only initialize in production
  if (process.env.NODE_ENV !== "production") {
    return;
  }

  // Check if DSN is configured
  const dsn = import.meta.env.VITE_SENTRY_DSN || process.env.SENTRY_DSN;
  if (!dsn) {
    // Sentry not configured, silently skip
    return;
  }

  try {
    // Dynamically import Sentry (only in production)
    const Sentry = await import("@sentry/react");

    Sentry.init({
      dsn,
      environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || "production",
      release: import.meta.env.VITE_SENTRY_RELEASE || "unknown",

      // Performance monitoring
      tracesSampleRate: parseFloat(
        import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || "0.1",
      ),

      // Error sampling
      sampleRate: parseFloat(import.meta.env.VITE_SENTRY_SAMPLE_RATE || "1.0"),

      // Integrations
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],

      // Filter out common non-actionable errors
      beforeSend(event, hint) {
        // Filter out network errors that are likely user-side issues
        if (event.exception) {
          const error = hint.originalException;
          if (error instanceof Error) {
            // Network errors
            if (
              error.message.includes("NetworkError") ||
              error.message.includes("Failed to fetch") ||
              error.message.includes("Network request failed")
            ) {
              return null; // Don't send to Sentry
            }
          }
        }
        return event;
      },
    });

    sentryInitialized = true;
  } catch (error) {
    // Sentry initialization failed, but don't break the app
    console.warn("Sentry initialization failed:", error);
  }
}

export function isSentryEnabled(): boolean {
  return sentryInitialized;
}

export function captureException(
  error: Error,
  context?: Record<string, unknown>,
): void {
  if (!sentryInitialized) {
    return;
  }

  try {
    // @ts-expect-error - Sentry may not be installed
    if (window.Sentry) {
      // @ts-expect-error - Sentry may not be installed
      window.Sentry.captureException(error, {
        extra: context,
      });
    }
  } catch {
    // Sentry failed, silently continue
  }
}

export function captureMessage(
  message: string,
  level: "info" | "warning" | "error" = "info",
): void {
  if (!sentryInitialized) {
    return;
  }

  try {
    // @ts-expect-error - Sentry may not be installed
    if (window.Sentry) {
      // @ts-expect-error - Sentry may not be installed
      window.Sentry.captureMessage(message, {
        level,
      });
    }
  } catch {
    // Sentry failed, silently continue
  }
}

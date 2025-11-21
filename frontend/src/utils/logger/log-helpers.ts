type LogLevel = "debug" | "info" | "warn" | "error";

export function shouldLogToConsole(
  isDev: boolean,
  level: LogLevel,
  sentryEnabled: boolean,
): boolean {
  if (isDev) return true;
  return level === "error" && !sentryEnabled;
}

export function getConsoleMethod(level: LogLevel) {
  return console[level] || console.log;
}

export function captureSentryError(message: string, args: unknown[]): void {
  try {
    // @ts-expect-error - Sentry may not be installed
    if (window.Sentry) {
      // @ts-expect-error - Sentry may not be installed
      window.Sentry.captureException(new Error(message), {
        extra: { args },
      });
    }
  } catch {
    // Sentry failed, silently continue
  }
}

export function captureSentryWarning(message: string, args: unknown[]): void {
  try {
    // @ts-expect-error - Sentry may not be installed
    if (window.Sentry) {
      // @ts-expect-error - Sentry may not be installed
      window.Sentry.captureMessage(message, {
        level: "warning",
        extra: { args },
      });
    }
  } catch {
    // Sentry failed, silently continue
  }
}

export function sendToSentry(
  level: LogLevel,
  message: string,
  args: unknown[],
): void {
  if (level === "error") {
    captureSentryError(message, args);
  } else if (level === "warn") {
    captureSentryWarning(message, args);
  }
}

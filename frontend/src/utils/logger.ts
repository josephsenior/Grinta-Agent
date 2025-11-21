/**
 * Production-safe logging utility.
 *
 * In development: logs to console
 * In production: sends to Sentry (if configured) and suppresses console output
 */

type LogLevel = "debug" | "info" | "warn" | "error";

class Logger {
  private isDev = process.env.NODE_ENV === "development";

  private sentryEnabled = false;

  constructor() {
    // Check if Sentry is available
    if (typeof window !== "undefined") {
      try {
        // @ts-expect-error - Sentry may not be installed
        if (window.Sentry) {
          this.sentryEnabled = true;
        }
      } catch {
        // Sentry not available
      }
    }
  }

  private async log(
    level: LogLevel,
    message: string,
    ...args: unknown[]
  ): Promise<void> {
    // Dynamic import to avoid circular dependencies
    const logHelpers = await import("./logger/log-helpers");
    const { shouldLogToConsole, getConsoleMethod, sendToSentry } = logHelpers;

    // In development, always log to console
    if (this.isDev) {
      const consoleMethod = getConsoleMethod(level);
      consoleMethod(`[${level.toUpperCase()}]`, message, ...args);
      return;
    }

    // In production, send to Sentry for errors/warnings
    if (this.sentryEnabled && (level === "error" || level === "warn")) {
      sendToSentry(level, message, args);
    }

    // In production, only log errors to console (for debugging)
    if (shouldLogToConsole(this.isDev, level, this.sentryEnabled)) {
      console.error(message, ...args);
    }
  }

  debug(message: string, ...args: unknown[]): void {
    this.log("debug", message, ...args).catch(() => {
      // Silently handle promise rejection
    });
  }

  info(message: string, ...args: unknown[]): void {
    this.log("info", message, ...args).catch(() => {
      // Silently handle promise rejection
    });
  }

  warn(message: string, ...args: unknown[]): void {
    this.log("warn", message, ...args).catch(() => {
      // Silently handle promise rejection
    });
  }

  error(message: string, ...args: unknown[]): void {
    this.log("error", message, ...args).catch(() => {
      // Silently handle promise rejection
    });
  }
}

// Export singleton instance
export const logger = new Logger();

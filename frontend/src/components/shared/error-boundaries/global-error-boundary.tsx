import React from "react";
import { AlertTriangle, RefreshCw, Bug } from "lucide-react";
import i18n from "#/i18n";
import { Button } from "#/components/ui/button";
import { logger } from "#/utils/logger";

interface GlobalErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface GlobalErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; retry: () => void }>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

/**
 * Global error boundary for the entire application
 * Catches unhandled errors and provides recovery options
 */
export class GlobalErrorBoundary extends React.Component<
  GlobalErrorBoundaryProps,
  GlobalErrorBoundaryState
> {
  constructor(props: GlobalErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): GlobalErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error("GlobalErrorBoundary caught an error:", error, errorInfo);

    const { onError } = this.props;
    // Log error to monitoring service
    if (onError) {
      onError(error, errorInfo);
    }

    // Update state with error info
    this.setState({
      error,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  static handleReload = (): void => {
    window.location.reload();
  };

  render() {
    const { hasError, error } = this.state;
    const { fallback, children } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback && error) {
        const FallbackComponent = fallback;
        return <FallbackComponent error={error} retry={this.handleRetry} />;
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-(--bg-primary) flex items-center justify-center p-8">
          <div className="text-center min-w-80 max-w-2xl px-4">
            <div className="mb-8">
              <AlertTriangle className="w-20 h-20 text-destructive mx-auto mb-6" />
              <h1 className="text-2xl font-bold text-(--text-primary) mb-3">
                {i18n.t("error.somethingWentWrong", "Something went wrong")}
              </h1>
              <p
                className="text-(--text-secondary) mb-6 break-normal whitespace-normal"
              >
                {i18n.t(
                  "error.unexpectedErrorLogged",
                  "We encountered an unexpected error. This has been logged and we'll look into it.",
                )}
              </p>
            </div>

            {process.env.NODE_ENV === "development" && error && (
              <details className="mb-8 text-left">
                <summary className="cursor-pointer text-sm font-medium text-(--text-secondary) mb-3">
                  {i18n.t(
                    "error.errorDetailsDevelopment",
                    "Error Details (Development)",
                  )}
                </summary>
                <div className="bg-(--bg-elevated) p-4 rounded border border-(--border-primary)">
                  <div className="mb-3">
                    <strong className="text-(--text-primary)">
                      {i18n.t("error.error", "Error")}:
                    </strong>
                    <pre className="text-xs text-(--text-tertiary) mt-1 overflow-auto max-h-32">
                      {error.message}
                    </pre>
                  </div>
                  {error.stack && (
                    <div>
                      <strong className="text-[var(--text-primary)]">
                        {i18n.t("error.stackTrace", "Stack Trace")}:
                      </strong>
                      <pre className="text-xs text-[var(--text-tertiary)] mt-1 overflow-auto max-h-48">
                        {error.stack}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}

            <div className="flex gap-4 justify-center">
              <Button
                onClick={this.handleRetry}
                variant="default"
                className="flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {i18n.t("common.tryAgain", "Try Again")}
              </Button>

              <Button
                onClick={GlobalErrorBoundary.handleReload}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Bug className="w-4 h-4" />
                {i18n.t("common.reloadPage", "Reload Page")}
              </Button>
            </div>

            <div
              className="mt-8 text-xs text-[var(--text-tertiary)] break-normal whitespace-normal"
            >
              {i18n.t(
                "error.contactSupportIfPersists",
                "If this problem persists, please contact support with the error details above.",
              )}
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Hook to use error boundary functionality in functional components
 */
export function useGlobalErrorBoundary() {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((err: Error) => {
    logger.error("Captured global error:", err);
    setError(err);
  }, []);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { captureError, resetError };
}

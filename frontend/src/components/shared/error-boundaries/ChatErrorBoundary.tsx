import React from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import i18n from "#/i18n";
import { Button } from "#/components/ui/button";
import { logger } from "#/utils/logger";

interface ChatErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ChatErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; retry: () => void }>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

/**
 * Error boundary specifically designed for chat interface
 * Provides graceful error handling with recovery options
 */
export class ChatErrorBoundary extends React.Component<
  ChatErrorBoundaryProps,
  ChatErrorBoundaryState
> {
  constructor(props: ChatErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ChatErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error("ChatErrorBoundary caught an error:", error, errorInfo);

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

  static handleGoHome = (): void => {
    window.location.href = "/";
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
        <div className="flex items-center justify-center min-h-[60vh] p-8">
          <div className="text-center min-w-[320px] max-w-2xl px-4">
            <div className="mb-6">
              <AlertTriangle className="w-16 h-16 text-destructive mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">
                {i18n.t("error.chatError", "Chat Error")}
              </h2>
              <p
                className="text-[var(--text-secondary)] mb-4"
                style={{ wordBreak: "normal", whiteSpace: "normal" }}
              >
                {i18n.t(
                  "error.chatErrorDescription",
                  "Something went wrong with the chat interface. This might be a temporary issue.",
                )}
              </p>
            </div>

            {process.env.NODE_ENV === "development" && error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-sm font-medium text-[var(--text-secondary)] mb-2">
                  {i18n.t(
                    "error.errorDetailsDevelopment",
                    "Error Details (Development)",
                  )}
                </summary>
                <pre className="text-xs bg-[var(--bg-elevated)] p-3 rounded border border-[var(--border-primary)] text-[var(--text-tertiary)] overflow-auto max-h-32">
                  {error.message}
                  {error.stack}
                </pre>
              </details>
            )}

            <div className="flex gap-3 justify-center">
              <Button
                onClick={this.handleRetry}
                variant="default"
                className="flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {i18n.t("common.tryAgain", "Try Again")}
              </Button>

              <Button
                onClick={ChatErrorBoundary.handleGoHome}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                {i18n.t("common.goHome", "Go Home")}
              </Button>
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
export function useChatErrorBoundary() {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((err: Error) => {
    logger.error("Captured error in chat:", err);
    setError(err);
  }, []);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { captureError, resetError };
}

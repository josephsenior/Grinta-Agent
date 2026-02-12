import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react";
import i18n from "#/i18n";
import { logger } from "#/utils/logger";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  retryCount: number;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  maxRetries?: number;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  private readonly retryTimeoutId: NodeJS.Timeout | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({
      error,
    });

    const { onError } = this.props;
    // Call the onError callback if provided
    if (onError) {
      onError(error, errorInfo);
    }

    // Log error in development
    if (process.env.NODE_ENV === "development") {
      logger.error("ErrorBoundary caught an error:", error, errorInfo);
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  handleRetry = (): void => {
    const { maxRetries = 3 } = this.props;
    const { retryCount } = this.state;

    if (retryCount < maxRetries) {
      this.setState((prevState) => ({
        hasError: false,
        error: null,
        retryCount: prevState.retryCount + 1,
      }));
    }
  };

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      retryCount: 0,
    });
  };

  // eslint-disable-next-line class-methods-use-this
  handleGoHome = (): void => {
    window.location.href = "/conversations";
  };

  render() {
    const { hasError, error, retryCount } = this.state;
    const { children, fallback, maxRetries = 3 } = this.props;

    if (hasError) {
      if (fallback) {
        return fallback;
      }

      return (
        <div
          className="min-h-screen flex items-center justify-center p-4 bg-[#111827]"
        >
          <div className="max-w-[28rem] w-full">
            <div
              className="bg-[#1f2937] border border-[#374151] rounded-2xl p-8 text-center"
            >
              {/* Error Icon */}
              <div
                className="flex justify-center mb-6"
              >
                <div
                  className="p-4 bg-red-500/10 rounded-full"
                >
                  <AlertTriangle
                    className="w-12 h-12 text-red-500"
                  />
                </div>
              </div>

              {/* Error Title */}
              <div className="mb-6">
                <h2
                  className="text-2xl font-bold text-white mb-2"
                >
                  {i18n.t(
                    "error.oopsSomethingWentWrong",
                    "Oops! Something went wrong",
                  )}
                </h2>
                <p className="text-gray-300">
                  {i18n.t(
                    "error.unexpectedErrorDontWorry",
                    "We encountered an unexpected error. Don't worry, we're on it!",
                  )}
                </p>
              </div>

              {/* Error Details (Always show in OSS Mode) */}
              {error && (
                <details
                  className="text-left bg-[#374151] rounded-lg p-4 mb-6"
                >
                  <summary
                    className="cursor-pointer text-sm font-medium text-gray-300 mb-2"
                  >
                    {i18n.t(
                      "error.errorDetails",
                      "Error Details",
                    )}
                  </summary>
                  <pre
                    className="text-xs text-gray-400 overflow-auto max-h-48 whitespace-pre-wrap select-text"
                  >
                    {/* Check if it's an API error with backend details */}
                    {(error as any).response?.data?.technical_details || (error as any).response?.data?.message || error.message}
                    {error.stack && `\n\nClient Stack:\n${error.stack}`}
                  </pre>
                </details>
              )}

              {/* Action Buttons */}
              <div
                className="flex flex-col gap-3"
              >
                {retryCount < maxRetries && (
                  <button
                    type="button"
                    onClick={this.handleRetry}
                    className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-blue-500 text-white rounded-xl border-none cursor-pointer font-medium hover:bg-blue-600 focus:bg-blue-600"
                  >
                    <RefreshCw className="w-4 h-4" />
                    {i18n.t("common.tryAgain", "Try Again")} (
                    {maxRetries - retryCount} {i18n.t("common.left", "left")})
                  </button>
                )}

                <button
                  type="button"
                  onClick={this.handleReset}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-[#374151] text-white rounded-xl border border-[#4b5563] cursor-pointer font-medium hover:bg-[#4b5563] focus:bg-[#4b5563]"
                >
                  <Bug className="w-4 h-4" />
                  {i18n.t("common.reset", "Reset")}
                </button>

                <button
                  type="button"
                  onClick={this.handleGoHome}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-[#374151] text-white rounded-xl border border-[#4b5563] cursor-pointer font-medium hover:bg-[#4b5563] focus:bg-[#4b5563]"
                >
                  <Home className="w-4 h-4" />
                  {i18n.t("common.goToConversations", "Go to Conversations")}
                </button>
              </div>

              {/* Retry Count Info */}
              {retryCount > 0 ? (
                <p
                  className="text-sm text-gray-400 mt-4"
                >
                  {i18n.t("error.retryAttempt", "Retry attempt")}: {retryCount}/
                  {maxRetries}
                </p>
              ) : null}
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

// Hook for functional components to trigger error boundary
export function useErrorHandler() {
  return (err: Error) => {
    // This will be caught by the nearest ErrorBoundary
    throw err;
  };
}

// Higher-order component for easier error boundary wrapping
export function withErrorBoundary<P extends object>(
  Wrapped: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">,
) {
  function WrappedComponent(props: P) {
    return (
      // eslint-disable-next-line react/jsx-props-no-spreading
      <ErrorBoundary {...errorBoundaryProps}>
        {/* eslint-disable-next-line react/jsx-props-no-spreading */}
        <Wrapped {...props} />
      </ErrorBoundary>
    );
  }

  WrappedComponent.displayName = `withErrorBoundary(${Wrapped.displayName || Wrapped.name})`;

  return WrappedComponent;
}

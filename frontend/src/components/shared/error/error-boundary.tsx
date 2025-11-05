import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home, Bug } from "lucide-react";

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

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
    });

    // Call the onError callback if provided
    this.props.onError?.(error, errorInfo);

    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  handleRetry = () => {
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

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      retryCount: 0,
    });
  };

  handleGoHome = () => {
    window.location.href = "/";
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
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            backgroundColor: "#111827",
          }}
        >
          <div style={{ maxWidth: "28rem", width: "100%" }}>
            <div
              style={{
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "1rem",
                padding: "2rem",
                textAlign: "center",
              }}
            >
              {/* Error Icon */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  marginBottom: "1.5rem",
                }}
              >
                <div
                  style={{
                    padding: "1rem",
                    backgroundColor: "rgba(239, 68, 68, 0.1)",
                    borderRadius: "50%",
                  }}
                >
                  <AlertTriangle
                    style={{ width: "3rem", height: "3rem", color: "#ef4444" }}
                  />
                </div>
              </div>

              {/* Error Title */}
              <div style={{ marginBottom: "1.5rem" }}>
                <h2
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: "bold",
                    color: "white",
                    marginBottom: "0.5rem",
                  }}
                >
                  Oops! Something went wrong
                </h2>
                <p style={{ color: "#d1d5db" }}>
                  We encountered an unexpected error. Don't worry, we're on it!
                </p>
              </div>

              {/* Error Details (Development Only) */}
              {process.env.NODE_ENV === "development" && error && (
                <details
                  style={{
                    textAlign: "left",
                    backgroundColor: "#374151",
                    borderRadius: "0.5rem",
                    padding: "1rem",
                    marginBottom: "1.5rem",
                  }}
                >
                  <summary
                    style={{
                      cursor: "pointer",
                      fontSize: "0.875rem",
                      fontWeight: "500",
                      color: "#d1d5db",
                      marginBottom: "0.5rem",
                    }}
                  >
                    Error Details (Development)
                  </summary>
                  <pre
                    style={{
                      fontSize: "0.75rem",
                      color: "#9ca3af",
                      overflow: "auto",
                      maxHeight: "8rem",
                    }}
                  >
                    {error.message}
                    {error.stack && `\n\n${error.stack}`}
                  </pre>
                </details>
              )}

              {/* Action Buttons */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                }}
              >
                {retryCount < maxRetries && (
                  <button
                    type="button"
                    onClick={this.handleRetry}
                    style={{
                      flex: 1,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "0.5rem",
                      padding: "0.75rem 1rem",
                      backgroundColor: "#3b82f6",
                      color: "white",
                      borderRadius: "0.75rem",
                      border: "none",
                      cursor: "pointer",
                      fontWeight: "500",
                    }}
                    onMouseOver={(e) => {
                      const t = e.target as HTMLElement | null;
                      if (t) t.style.backgroundColor = "#2563eb";
                    }}
                    onMouseOut={(e) => {
                      const t = e.target as HTMLElement | null;
                      if (t) t.style.backgroundColor = "#3b82f6";
                    }}
                    onFocus={(e) => {
                      const t = e.target as HTMLElement | null;
                      if (t) t.style.backgroundColor = "#2563eb";
                    }}
                    onBlur={(e) => {
                      const t = e.target as HTMLElement | null;
                      if (t) t.style.backgroundColor = "#3b82f6";
                    }}
                  >
                    <RefreshCw style={{ width: "1rem", height: "1rem" }} />
                    Try Again ({maxRetries - retryCount} left)
                  </button>
                )}

                <button
                  type="button"
                  onClick={this.handleReset}
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "0.5rem",
                    padding: "0.75rem 1rem",
                    backgroundColor: "#374151",
                    color: "white",
                    borderRadius: "0.75rem",
                    border: "1px solid #4b5563",
                    cursor: "pointer",
                    fontWeight: "500",
                  }}
                  onMouseOver={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#4b5563";
                  }}
                  onMouseOut={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#374151";
                  }}
                  onFocus={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#4b5563";
                  }}
                  onBlur={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#374151";
                  }}
                >
                  <Bug style={{ width: "1rem", height: "1rem" }} />
                  Reset
                </button>

                <button
                  type="button"
                  onClick={this.handleGoHome}
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "0.5rem",
                    padding: "0.75rem 1rem",
                    backgroundColor: "#374151",
                    color: "white",
                    borderRadius: "0.75rem",
                    border: "1px solid #4b5563",
                    cursor: "pointer",
                    fontWeight: "500",
                  }}
                  onMouseOver={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#4b5563";
                  }}
                  onMouseOut={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#374151";
                  }}
                  onFocus={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#4b5563";
                  }}
                  onBlur={(e) => {
                    const t = e.target as HTMLElement | null;
                    if (t) t.style.backgroundColor = "#374151";
                  }}
                >
                  <Home style={{ width: "1rem", height: "1rem" }} />
                  Go Home
                </button>
              </div>

              {/* Retry Count Info */}
              {retryCount > 0 && (
                <p
                  style={{
                    fontSize: "0.875rem",
                    color: "#9ca3af",
                    marginTop: "1rem",
                  }}
                >
                  Retry attempt: {retryCount}/{maxRetries}
                </p>
              )}
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
  return (error: Error) => {
    // This will be caught by the nearest ErrorBoundary
    throw error;
  };
}

// Higher-order component for easier error boundary wrapping
export function withErrorBoundary<P extends object>(
  Wrapped: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">,
) {
  function WrappedComponent(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Wrapped {...props} />
      </ErrorBoundary>
    );
  }

  WrappedComponent.displayName = `withErrorBoundary(${Wrapped.displayName || Wrapped.name})`;

  return WrappedComponent;
}

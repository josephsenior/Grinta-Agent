import React from "react";
import { AlertTriangle, RefreshCw, Bug } from "lucide-react";
import { Button } from "#/components/ui/button";

interface GlobalErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
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
    console.error("GlobalErrorBoundary caught an error:", error, errorInfo);

    // Log error to monitoring service
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Update state with error info
    this.setState({
      error,
      errorInfo,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback && this.state.error) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent
            error={this.state.error}
            retry={this.handleRetry}
          />
        );
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-background-primary flex items-center justify-center p-8">
          <div className="text-center max-w-lg">
            <div className="mb-8">
              <AlertTriangle className="w-20 h-20 text-destructive mx-auto mb-6" />
              <h1 className="text-2xl font-bold text-text-primary mb-3">
                Something went wrong
              </h1>
              <p className="text-text-secondary mb-6">
                We encountered an unexpected error. This has been logged and
                we'll look into it.
              </p>
            </div>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className="mb-8 text-left">
                <summary className="cursor-pointer text-sm font-medium text-text-secondary mb-3">
                  Error Details (Development)
                </summary>
                <div className="bg-background-secondary p-4 rounded border">
                  <div className="mb-3">
                    <strong className="text-text-primary">Error:</strong>
                    <pre className="text-xs text-text-tertiary mt-1 overflow-auto max-h-32">
                      {this.state.error.message}
                    </pre>
                  </div>
                  {this.state.error.stack && (
                    <div>
                      <strong className="text-text-primary">
                        Stack Trace:
                      </strong>
                      <pre className="text-xs text-text-tertiary mt-1 overflow-auto max-h-48">
                        {this.state.error.stack}
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
                Try Again
              </Button>

              <Button
                onClick={this.handleReload}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Bug className="w-4 h-4" />
                Reload Page
              </Button>
            </div>

            <div className="mt-8 text-xs text-text-tertiary">
              If this problem persists, please contact support with the error
              details above.
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
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

  const captureError = React.useCallback((error: Error) => {
    console.error("Captured global error:", error);
    setError(error);
  }, []);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { captureError, resetError };
}

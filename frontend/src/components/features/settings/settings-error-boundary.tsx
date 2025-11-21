import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "#/components/ui/button";
import { logger } from "#/utils/logger";

interface SettingsErrorBoundaryProps {
  children: React.ReactNode;
  fallbackMessage?: string;
}

interface SettingsErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/**
 * Error boundary specifically for settings components
 * Provides a graceful fallback UI when settings fail to load or save
 */
export class SettingsErrorBoundary extends React.Component<
  SettingsErrorBoundaryProps,
  SettingsErrorBoundaryState
> {
  constructor(props: SettingsErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(
    error: Error,
  ): Partial<SettingsErrorBoundaryState> {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    logger.error("[SettingsErrorBoundary] Caught error:", error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Reload the page to reset all settings state
    window.location.reload();
  };

  static handleResetSettings = (): void => {
    // Clear localStorage settings
    const settingsKeys = Object.keys(localStorage).filter(
      (key) => key.startsWith("Forge.") || key.includes("settings"),
    );

    settingsKeys.forEach((key) => localStorage.removeItem(key));

    // Reload
    window.location.reload();
  };

  render() {
    const { hasError, error, errorInfo } = this.state;
    const { fallbackMessage, children } = this.props;

    if (hasError) {
      return (
        <div className="flex items-center justify-center min-h-[400px] p-6">
          <div className="max-w-md w-full bg-background-secondary border border-danger-500/20 rounded-xl p-6 space-y-4">
            {/* Icon */}
            <div className="flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-danger-500/10 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-danger-500" />
              </div>
            </div>

            {/* Title */}
            <div className="text-center">
              {/* eslint-disable-next-line i18next/no-literal-string */}
              <h2 className="text-lg font-semibold text-text-primary mb-2">
                Settings Error
              </h2>
              <p className="text-sm text-text-secondary">
                {fallbackMessage ||
                  "An error occurred while loading or saving your settings. This might be due to corrupted data or a connection issue."}
              </p>
            </div>

            {/* Error Details (Development Only) */}
            {process.env.NODE_ENV === "development" && error && (
              <details className="mt-4 p-3 bg-background-tertiary rounded-lg">
                {/* eslint-disable-next-line i18next/no-literal-string */}
                <summary className="text-xs font-medium text-text-secondary cursor-pointer hover:text-text-primary">
                  Error Details (Dev Only)
                </summary>
                <div className="mt-2 space-y-2">
                  <p className="text-xs text-danger-500 font-mono break-all">
                    {error.toString()}
                  </p>
                  {errorInfo && (
                    <pre className="text-[10px] text-text-tertiary overflow-auto max-h-32">
                      {errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            {/* Actions */}
            <div className="flex flex-col gap-2 pt-2">
              {/* eslint-disable-next-line i18next/no-literal-string */}
              <Button
                type="button"
                onClick={this.handleReset}
                className="w-full bg-brand-500 hover:bg-brand-600 text-white"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Reload Page
              </Button>

              {/* eslint-disable-next-line i18next/no-literal-string */}
              <Button
                type="button"
                onClick={() => {
                  SettingsErrorBoundary.handleResetSettings();
                }}
                variant="outline"
                className="w-full border-danger-500/20 hover:bg-danger-500/10 text-danger-500"
              >
                <AlertTriangle className="w-4 h-4 mr-2" />
                Reset Settings & Reload
              </Button>

              {/* eslint-disable-next-line i18next/no-literal-string */}
              <p className="text-xs text-text-tertiary text-center mt-2">
                If the problem persists, try clearing your browser cache or
                contact support.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * User-Friendly Error Display Component
 * 
 * Beautiful, actionable error messages that help users understand and resolve issues.
 * 
 * Features:
 * - Clear, non-technical language
 * - Visual hierarchy with icons
 * - Actionable buttons
 * - Collapsible technical details
 * - Retry functionality
 * - Help links
 */

import React from "react";
import { AlertTriangle, Info, AlertCircle, XCircle, RefreshCw, HelpCircle, ExternalLink } from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

export interface ErrorAction {
  label: string;
  type: string;  // "retry", "new_conversation", "help", "upgrade", etc.
  url?: string;
  highlight?: boolean;
  data?: Record<string, unknown>;
}

export interface UserFriendlyErrorData {
  title: string;
  message: string;
  severity: "info" | "warning" | "error" | "critical";
  category: "user_input" | "system" | "rate_limit" | "authentication" | "network" | "ai_model" | "configuration";
  icon?: string;
  suggestion?: string;
  actions?: ErrorAction[];
  technical_details?: string;
  error_code?: string;
  can_retry?: boolean;
  retry_delay?: number;
  help_url?: string;
  reassurance?: string;
  metadata?: Record<string, unknown>;
  timestamp?: string;
}

interface UserFriendlyErrorProps {
  error: UserFriendlyErrorData;
  onAction?: (action: ErrorAction) => void;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  showActions?: boolean;
}

const SEVERITY_CONFIG = {
  info: {
    icon: Info,
    color: "text-blue-500",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    iconBg: "bg-blue-500/20"
  },
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    iconBg: "bg-yellow-500/20"
  },
  error: {
    icon: AlertCircle,
    color: "text-red-500",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    iconBg: "bg-red-500/20"
  },
  critical: {
    icon: XCircle,
    color: "text-red-600",
    bg: "bg-red-600/15",
    border: "border-red-600/40",
    iconBg: "bg-red-600/25"
  }
};

export function UserFriendlyError({
  error,
  onAction,
  onRetry,
  onDismiss,
  className,
  showActions = true
}: UserFriendlyErrorProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = React.useState(false);
  const [retryCountdown, setRetryCountdown] = React.useState<number | null>(null);

  const config = SEVERITY_CONFIG[error.severity];
  const IconComponent = config.icon;

  // Handle retry countdown
  React.useEffect(() => {
    if (error.retry_delay && error.can_retry) {
      setRetryCountdown(error.retry_delay);
      
      const interval = setInterval(() => {
        setRetryCountdown(prev => {
          if (prev === null || prev <= 1) {
            clearInterval(interval);
            return null;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [error.retry_delay, error.can_retry]);

  const handleAction = (action: ErrorAction) => {
    if (action.type === "retry" && onRetry) {
      onRetry();
    } else if (action.type === "refresh") {
      window.location.reload();
    } else if (action.url) {
      window.open(action.url, "_blank");
    } else if (onAction) {
      onAction(action);
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border-2 p-4 sm:p-6 space-y-4 animate-fade-in-up",
        config.bg,
        config.border,
        "shadow-lg backdrop-blur-sm",
        className
      )}
      role="alert"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-start gap-3 sm:gap-4">
        {/* Icon */}
        <div className={cn(
          "flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center",
          config.iconBg,
          "shadow-md"
        )}>
          {error.icon ? (
            <span className="text-2xl sm:text-3xl">{error.icon}</span>
          ) : (
            <IconComponent className={cn("h-5 w-5 sm:h-6 sm:w-6", config.color)} />
          )}
        </div>

        {/* Title and dismiss */}
        <div className="flex-1 min-w-0">
          <h3 className={cn("text-base sm:text-lg font-semibold", config.color)}>
            {error.title}
          </h3>
          {error.error_code && (
            <p className="text-xs text-text-tertiary mt-0.5">
              Error Code: {error.error_code}
            </p>
          )}
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1 rounded-lg hover:bg-background-elevated/50 transition-colors"
            aria-label="Dismiss error"
          >
            <XCircle className="h-5 w-5 text-text-tertiary hover:text-text-secondary" />
          </button>
        )}
      </div>

      {/* Message */}
      <div className="space-y-3">
        <div className="text-sm sm:text-base text-text-primary whitespace-pre-line leading-relaxed">
          {error.message}
        </div>

        {/* Suggestion */}
        {error.suggestion && (
          <div className={cn(
            "flex items-start gap-2 p-3 rounded-lg",
            "bg-brand-500/5 border border-brand-500/20"
          )}>
            <HelpCircle className="h-4 w-4 text-brand-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-text-secondary">
              <span className="font-medium text-brand-500">Suggestion:</span> {error.suggestion}
            </p>
          </div>
        )}

        {/* Reassurance */}
        {error.reassurance && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
            <Info className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-green-400">
              {error.reassurance}
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      {showActions && error.actions && error.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {error.actions.map((action, index) => (
            <Button
              key={index}
              onClick={() => handleAction(action)}
              variant={action.highlight ? "default" : "outline"}
              size="sm"
              className={cn(
                "transition-all duration-200",
                action.highlight && "shadow-md hover:shadow-lg",
                action.type === "retry" && retryCountdown && "opacity-50 cursor-not-allowed"
              )}
              disabled={action.type === "retry" && retryCountdown !== null && retryCountdown > 0}
            >
              {action.type === "retry" && retryCountdown && retryCountdown > 0 ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1.5" />
                  Retry in {retryCountdown}s
                </>
              ) : (
                <>
                  {action.type === "retry" && <RefreshCw className="h-4 w-4 mr-1.5" />}
                  {action.type === "help" && <HelpCircle className="h-4 w-4 mr-1.5" />}
                  {action.url && <ExternalLink className="h-4 w-4 mr-1.5" />}
                  {action.label}
                </>
              )}
            </Button>
          ))}
        </div>
      )}

      {/* Help Link */}
      {error.help_url && (
        <div className="pt-2 border-t border-border-subtle">
          <a
            href={error.help_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-brand-500 hover:text-brand-400 inline-flex items-center gap-1 transition-colors"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            Learn more in our documentation
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      )}

      {/* Technical Details (Collapsible) */}
      {error.technical_details && (
        <div className="pt-3 border-t border-border-subtle">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="flex items-center gap-2 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
          >
            <span>{showTechnicalDetails ? "▼" : "▶"}</span>
            <span>Technical details {showTechnicalDetails ? "(hide)" : "(show)"}</span>
          </button>
          
          {showTechnicalDetails && (
            <div className="mt-3 p-3 rounded-lg bg-black/40 border border-border-subtle">
              <pre className="text-xs text-text-tertiary font-mono overflow-x-auto whitespace-pre-wrap break-words">
                {error.technical_details}
              </pre>
              {error.timestamp && (
                <p className="text-xs text-text-muted mt-2">
                  Timestamp: {new Date(error.timestamp).toLocaleString()}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact error banner (for inline display)
 */
export function ErrorBanner({ error, onDismiss, className }: {
  error: UserFriendlyErrorData;
  onDismiss?: () => void;
  className?: string;
}) {
  const config = SEVERITY_CONFIG[error.severity];
  const IconComponent = config.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg border",
        config.bg,
        config.border,
        className
      )}
      role="alert"
    >
      {/* Icon */}
      <div className={cn("flex-shrink-0", config.color)}>
        {error.icon ? (
          <span className="text-lg">{error.icon}</span>
        ) : (
          <IconComponent className="h-5 w-5" />
        )}
      </div>

      {/* Message */}
      <div className="flex-1 min-w-0">
        <p className={cn("text-sm font-medium", config.color)}>
          {error.title}
        </p>
        {error.suggestion && (
          <p className="text-xs text-text-secondary mt-0.5">
            {error.suggestion}
          </p>
        )}
      </div>

      {/* Dismiss */}
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 p-1 rounded hover:bg-background-elevated/50 transition-colors"
          aria-label="Dismiss"
        >
          <XCircle className="h-4 w-4 text-text-tertiary" />
        </button>
      )}
    </div>
  );
}


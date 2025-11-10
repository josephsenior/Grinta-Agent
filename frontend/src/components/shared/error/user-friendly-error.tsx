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
import {
  AlertTriangle,
  Info,
  AlertCircle,
  XCircle,
  RefreshCw,
  HelpCircle,
  ExternalLink,
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";

export interface ErrorAction {
  label: string;
  type: string; // "retry", "new_conversation", "help", "upgrade", etc.
  url?: string;
  highlight?: boolean;
  data?: Record<string, unknown>;
}

export interface UserFriendlyErrorData {
  title: string;
  message: string;
  severity: "info" | "warning" | "error" | "critical";
  category:
    | "user_input"
    | "system"
    | "rate_limit"
    | "authentication"
    | "network"
    | "ai_model"
    | "configuration";
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
    iconBg: "bg-blue-500/20",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    iconBg: "bg-yellow-500/20",
  },
  error: {
    icon: AlertCircle,
    color: "text-red-500",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    iconBg: "bg-red-500/20",
  },
  critical: {
    icon: XCircle,
    color: "text-red-600",
    bg: "bg-red-600/15",
    border: "border-red-600/40",
    iconBg: "bg-red-600/25",
  },
};

export function UserFriendlyError({
  error,
  onAction,
  onRetry,
  onDismiss,
  className,
  showActions = true,
}: UserFriendlyErrorProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = React.useState(false);
  const config = React.useMemo(
    () => SEVERITY_CONFIG[error.severity],
    [error.severity],
  );
  const IconComponent = config.icon;
  const retryCountdown = useRetryCountdown(error);
  const handleAction = useErrorActionHandler({ onRetry, onAction });

  return (
    <div
      className={cn(
        "rounded-xl border-2 p-4 sm:p-6 space-y-4 animate-fade-in-up",
        config.bg,
        config.border,
        "shadow-lg backdrop-blur-sm",
        className,
      )}
      role="alert"
      aria-live="polite"
    >
      <ErrorHeader
        error={error}
        config={config}
        IconComponent={IconComponent}
        onDismiss={onDismiss}
      />

      <ErrorMessageSection error={error} />

      {showActions && error.actions?.length ? (
        <ErrorActions
          actions={error.actions}
          onAction={handleAction}
          retryCountdown={retryCountdown}
        />
      ) : null}

      {error.help_url && <ErrorHelpLink helpUrl={error.help_url} />}

      {error.technical_details && (
        <TechnicalDetailsSection
          technicalDetails={error.technical_details}
          timestamp={error.timestamp}
          isExpanded={showTechnicalDetails}
          onToggle={() => setShowTechnicalDetails((prev) => !prev)}
        />
      )}
    </div>
  );
}

function useRetryCountdown(error: UserFriendlyErrorData) {
  const { retry_delay, can_retry } = error;
  const [retryCountdown, setRetryCountdown] = React.useState<number | null>(
    null,
  );

  React.useEffect(() => {
    if (!retry_delay || !can_retry) {
      setRetryCountdown(null);
      return;
    }

    setRetryCountdown(retry_delay);

    const interval = setInterval(() => {
      setRetryCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          return null;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [retry_delay, can_retry]);

  return retryCountdown;
}

function useErrorActionHandler({
  onRetry,
  onAction,
}: {
  onRetry?: () => void;
  onAction?: (action: ErrorAction) => void;
}) {
  return React.useCallback(
    (action: ErrorAction) => {
      if (action.type === "retry" && onRetry) {
        onRetry();
        return;
      }

      if (action.type === "refresh") {
        window.location.reload();
        return;
      }

      if (action.url) {
        window.open(action.url, "_blank");
        return;
      }

      onAction?.(action);
    },
    [onRetry, onAction],
  );
}

function ErrorHeader({
  error,
  config,
  IconComponent,
  onDismiss,
}: {
  error: UserFriendlyErrorData;
  config: (typeof SEVERITY_CONFIG)[UserFriendlyErrorData["severity"]];
  IconComponent: React.ComponentType<{ className?: string }>;
  onDismiss?: () => void;
}) {
  return (
    <div className="flex items-start gap-3 sm:gap-4">
      <div
        className={cn(
          "flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center",
          config.iconBg,
          "shadow-md",
        )}
      >
        {error.icon ? (
          <span className="text-2xl sm:text-3xl">{error.icon}</span>
        ) : (
          <IconComponent
            className={cn("h-5 w-5 sm:h-6 sm:w-6", config.color)}
          />
        )}
      </div>

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
  );
}

function ErrorMessageSection({ error }: { error: UserFriendlyErrorData }) {
  return (
    <div className="space-y-3">
      <div className="text-sm sm:text-base text-text-primary whitespace-pre-line leading-relaxed">
        {error.message}
      </div>

      {error.suggestion && (
        <div
          className={cn(
            "flex items-start gap-2 p-3 rounded-lg",
            "bg-brand-500/5 border border-brand-500/20",
          )}
        >
          <HelpCircle className="h-4 w-4 text-brand-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-text-secondary">
            <span className="font-medium text-brand-500">Suggestion:</span>{" "}
            {error.suggestion}
          </p>
        </div>
      )}

      {error.reassurance && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
          <Info className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-green-400">{error.reassurance}</p>
        </div>
      )}
    </div>
  );
}

function ErrorActions({
  actions,
  onAction,
  retryCountdown,
}: {
  actions: ErrorAction[];
  onAction: (action: ErrorAction) => void;
  retryCountdown: number | null;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action, index) => (
        <ErrorActionButton
          key={`${action.type}-${index}`}
          action={action}
          onAction={onAction}
          retryCountdown={retryCountdown}
        />
      ))}
    </div>
  );
}

function ErrorActionButton({
  action,
  onAction,
  retryCountdown,
}: {
  action: ErrorAction;
  onAction: (action: ErrorAction) => void;
  retryCountdown: number | null;
}) {
  const isRetry = action.type === "retry";
  const isWaiting = isRetry && retryCountdown !== null && retryCountdown > 0;

  return (
    <Button
      onClick={() => onAction(action)}
      variant={action.highlight ? "default" : "outline"}
      size="sm"
      className={cn(
        "transition-all duration-200",
        action.highlight && "shadow-md hover:shadow-lg",
        isWaiting && "opacity-50 cursor-not-allowed",
      )}
      disabled={isWaiting}
    >
      {isRetry ? (
        <RetryActionContent retryCountdown={retryCountdown} />
      ) : (
        <ActionContent action={action} />
      )}
    </Button>
  );
}

function RetryActionContent({
  retryCountdown,
}: {
  retryCountdown: number | null;
}) {
  if (!retryCountdown || retryCountdown <= 0) {
    return (
      <>
        <RefreshCw className="h-4 w-4 mr-1.5" />
        Retry
      </>
    );
  }

  return (
    <>
      <RefreshCw className="h-4 w-4 mr-1.5" />
      Retry in {retryCountdown}s
    </>
  );
}

function ActionContent({ action }: { action: ErrorAction }) {
  return (
    <>
      {action.type === "help" && <HelpCircle className="h-4 w-4 mr-1.5" />}
      {action.url && <ExternalLink className="h-4 w-4 mr-1.5" />}
      {action.label}
    </>
  );
}

function ErrorHelpLink({ helpUrl }: { helpUrl: string }) {
  return (
    <div className="pt-2 border-t border-border-subtle">
      <a
        href={helpUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-brand-500 hover:text-brand-400 inline-flex items-center gap-1 transition-colors"
      >
        <HelpCircle className="h-3.5 w-3.5" />
        Learn more in our documentation
        <ExternalLink className="h-3 w-3" />
      </a>
    </div>
  );
}

function TechnicalDetailsSection({
  technicalDetails,
  timestamp,
  isExpanded,
  onToggle,
}: {
  technicalDetails: string;
  timestamp?: string;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="pt-3 border-t border-border-subtle">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-xs text-text-tertiary hover:text-text-secondary transition-colors"
      >
        <span>{isExpanded ? "▼" : "▶"}</span>
        <span>Technical details {isExpanded ? "(hide)" : "(show)"}</span>
      </button>

      {isExpanded && (
        <div className="mt-3 p-3 rounded-lg bg-black/40 border border-border-subtle">
          <pre className="text-xs text-text-tertiary font-mono overflow-x-auto whitespace-pre-wrap break-words">
            {technicalDetails}
          </pre>
          {timestamp && (
            <p className="text-xs text-text-muted mt-2">
              Timestamp: {new Date(timestamp).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact error banner (for inline display)
 */
export function ErrorBanner({
  error,
  onDismiss,
  className,
}: {
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
        className,
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
        <p className={cn("text-sm font-medium", config.color)}>{error.title}</p>
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

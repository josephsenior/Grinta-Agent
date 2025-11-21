import { Trans } from "react-i18next";
import { Link } from "react-router-dom";
import { AlertTriangle, X, RefreshCw, ExternalLink } from "lucide-react";
import { useState } from "react";
import i18n from "#/i18n";
import { cn } from "#/utils/utils";
import { ErrorBanner } from "#/components/shared/error/user-friendly-error";
import { extractUserFriendlyError } from "#/utils/format-error";

interface ErrorMessageBannerProps {
  message: string;
  type?: "error" | "warning" | "info";
  dismissible?: boolean;
  onDismiss?: () => void;
  onRetry?: () => void;
  retryLabel?: string;
  showDetails?: boolean;
  className?: string;
  error?: unknown; // Raw error object for user-friendly formatting
}

type BannerVariant = NonNullable<ErrorMessageBannerProps["type"]>;

const BANNER_STYLES: Record<
  BannerVariant,
  { container: string; icon: string; button: string }
> = {
  error: {
    container:
      "bg-danger-DEFAULT/10 border-danger-DEFAULT/20 text-danger-DEFAULT",
    icon: "text-danger-DEFAULT",
    button: "hover:bg-danger-DEFAULT/20 text-danger-DEFAULT",
  },
  warning: {
    container:
      "bg-warning-DEFAULT/10 border-warning-DEFAULT/20 text-warning-DEFAULT",
    icon: "text-warning-DEFAULT",
    button: "hover:bg-warning-DEFAULT/20 text-warning-DEFAULT",
  },
  info: {
    container: "bg-info-DEFAULT/10 border-info-DEFAULT/20 text-info-DEFAULT",
    icon: "text-info-DEFAULT",
    button: "hover:bg-info-DEFAULT/20 text-info-DEFAULT",
  },
};

const renderBannerMessage = (message: string) =>
  i18n.exists(message) ? (
    <Trans
      i18nKey={message}
      components={{
        a: (
          <Link
            className="underline font-bold cursor-pointer hover:opacity-80 transition-opacity inline-flex items-center gap-1"
            to="/settings/billing"
          >
            link
            <ExternalLink className="w-3 h-3" />
          </Link>
        ),
      }}
    />
  ) : (
    message
  );

function DetailsSection({
  showDetails,
  showFullDetails,
  onToggle,
  rawMessage,
}: {
  showDetails: boolean;
  showFullDetails: boolean;
  onToggle: () => void;
  rawMessage: string;
}) {
  if (!showDetails) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        onClick={onToggle}
        className="mt-2 text-xs opacity-75 hover:opacity-100 transition-opacity"
      >
        {showFullDetails ? "Hide details" : "Show details"}
      </button>
      {showFullDetails && (
        <div className="mt-3 p-3 bg-background-elevated/50 rounded-lg text-xs font-mono">
          <pre className="whitespace-pre-wrap">{rawMessage}</pre>
        </div>
      )}
    </>
  );
}

export function ErrorMessageBanner({
  message,
  type = "error",
  dismissible = true,
  onDismiss,
  onRetry,
  retryLabel = "Retry",
  showDetails = false,
  className,
  error,
}: ErrorMessageBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);
  const [showFullDetails, setShowFullDetails] = useState(false);

  const styles = BANNER_STYLES[type];

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  if (isDismissed) return null;

  // Try to use user-friendly error if available
  const userFriendlyError = error ? extractUserFriendlyError(error) : null;

  if (userFriendlyError) {
    return (
      <ErrorBanner
        error={userFriendlyError}
        onDismiss={dismissible ? handleDismiss : undefined}
        className={className}
      />
    );
  }

  return (
    <div
      className={cn(
        "w-full rounded-xl border backdrop-blur-xl p-4 transition-all duration-300",
        "animate-slide-down shadow-lg",
        styles.container,
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 pt-0.5">
          <AlertTriangle className={cn("w-5 h-5", styles.icon)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium">
            {renderBannerMessage(message)}
          </div>

          <DetailsSection
            showDetails={showDetails}
            showFullDetails={showFullDetails}
            onToggle={() => setShowFullDetails((current) => !current)}
            rawMessage={
              typeof message === "string"
                ? message
                : JSON.stringify(message, null, 2)
            }
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                "hover:bg-background-elevated/50",
                styles.button,
              )}
              title={retryLabel}
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}

          {dismissible && (
            <button
              type="button"
              onClick={handleDismiss}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                "hover:bg-background-elevated/50",
                styles.button,
              )}
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

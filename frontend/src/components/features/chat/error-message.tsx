import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { useTranslation } from "react-i18next";
import { code } from "../markdown/code";
import { ol, ul } from "../markdown/list";
import ArrowDown from "#/icons/angle-down-solid.svg?react";
import ArrowUp from "#/icons/angle-up-solid.svg?react";
import i18n from "#/i18n";
import { UserFriendlyError } from "#/components/shared/error/user-friendly-error";
import { extractUserFriendlyError } from "#/utils/format-error";
import { useErrorActionHandler } from "#/hooks/use-error-action-handler";

interface ErrorMessageProps {
  errorId?: string;
  defaultMessage: string;
  error?: unknown; // Raw error object (for user-friendly formatting)
  onRetry?: () => void;
}

export function ErrorMessage({
  errorId,
  defaultMessage,
  error,
  onRetry,
}: ErrorMessageProps) {
  const { t } = useTranslation();
  const [showDetails, setShowDetails] = React.useState(false);
  const { handleErrorAction } = useErrorActionHandler();

  // Try to extract user-friendly error
  const userFriendlyError = error ? extractUserFriendlyError(error) : null;

  // If we have a user-friendly error, use the enhanced component
  if (userFriendlyError) {
    return (
      <div className="my-4">
        <UserFriendlyError
          error={userFriendlyError}
          onAction={(action) =>
            handleErrorAction(action, { retry: onRetry ?? (() => {}) })
          }
          onRetry={onRetry || (() => {})}
        />
      </div>
    );
  }

  // Fallback to legacy error display
  const hasValidTranslationId = !!errorId && i18n.exists(errorId);
  const errorKey = hasValidTranslationId
    ? errorId
    : "CHAT_INTERFACE$AGENT_ERROR_MESSAGE";

  return (
    <div className="flex flex-col gap-2 border-l-2 pl-2 my-2 py-2 border-danger text-sm w-full">
      <div className="font-bold text-danger">
        {t(errorKey)}
        <button
          type="button"
          onClick={() => setShowDetails((prev) => !prev)}
          className="cursor-pointer text-left"
          aria-label={showDetails ? "Hide error details" : "Show error details"}
        >
          {showDetails ? (
            <ArrowUp className="h-4 w-4 ml-2 inline fill-danger" />
          ) : (
            <ArrowDown className="h-4 w-4 ml-2 inline fill-danger" />
          )}
        </button>
      </div>

      {showDetails && (
        <Markdown
          components={{
            code,
            ul,
            ol,
          }}
          remarkPlugins={[remarkGfm, remarkBreaks]}
        >
          {defaultMessage}
        </Markdown>
      )}
    </div>
  );
}

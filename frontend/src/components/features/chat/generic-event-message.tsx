import React from "react";
import { cn } from "#/utils/utils";
import { SuccessIndicator } from "./success-indicator";
import { ObservationResultStatus } from "./event-content-helpers/get-observation-result";

interface GenericEventMessageProps {
  title: React.ReactNode;
  details: string | React.ReactNode;
  success?: ObservationResultStatus;
  initiallyExpanded?: boolean;
}

export function GenericEventMessage({
  title,
  details,
  success,
  initiallyExpanded = false,
}: GenericEventMessageProps) {
  const [isExpanded, setIsExpanded] = React.useState(initiallyExpanded);

  let successColor = "text-[var(--text-tertiary)]";
  if (success === "success") {
    successColor = "text-[var(--text-success)]";
  } else if (success === "error") {
    successColor = "text-[var(--text-danger)]";
  }

  let borderColor = "border-[var(--border-primary)]";
  if (success === "success") {
    borderColor = "border-[var(--text-success)]/30";
  } else if (success === "error") {
    borderColor = "border-[var(--text-danger)]/30";
  }

  let hoverBg = "hover:bg-[var(--bg-tertiary)]";
  if (success === "success") {
    hoverBg = "hover:bg-[var(--text-success)]/5";
  } else if (success === "error") {
    hoverBg = "hover:bg-[var(--text-danger)]/5";
  }

  return (
    <div
      className={cn(
        "my-2 w-full bg-[var(--bg-elevated)] border rounded-lg overflow-hidden",
        borderColor,
      )}
    >
      {/* Header - clickable to expand/collapse */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center justify-between gap-3 px-4 py-2.5 text-sm w-full transition-colors",
          hoverBg,
        )}
      >
        <div className="flex items-center gap-3">
          {success && <SuccessIndicator status={success} />}
          <div className={cn("font-medium", successColor)}>{title}</div>
        </div>
        <svg
          className={cn(
            "w-4 h-4 transition-transform",
            successColor,
            isExpanded && "rotate-180",
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Details content - shown when expanded */}
      {isExpanded && (
        <div className={cn("px-4 pb-3 border-t", borderColor)}>
          {typeof details === "string" ? (
            <div className="text-sm text-[var(--text-primary)] mt-2">
              {details}
            </div>
          ) : (
            details
          )}
        </div>
      )}
    </div>
  );
}

import React from "react";
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

  return (
    <div className="my-2 w-full bg-gradient-to-r from-success-500/10 to-success-600/5 border border-success-500/20 rounded-xl backdrop-blur-sm overflow-hidden">
      {/* Header - clickable to expand/collapse */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between gap-3 px-4 py-3 text-sm w-full hover:bg-success-500/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          {success && <SuccessIndicator status={success} />}
          <div className="text-success-400 font-medium">{title}</div>
        </div>
        <svg
          className={`w-5 h-5 text-success-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
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
        <div className="px-4 pb-4 border-t border-success-500/10">
          {typeof details === "string" ? (
            <div className="text-sm text-foreground-secondary">{details}</div>
          ) : (
            details
          )}
        </div>
      )}
    </div>
  );
}

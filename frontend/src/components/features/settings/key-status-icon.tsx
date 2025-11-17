import SuccessIcon from "#/icons/success.svg?react";
import { cn } from "#/utils/utils";

interface KeyStatusIconProps {
  testId?: string;
  isSet: boolean;
}

export function KeyStatusIcon({ testId, isSet }: KeyStatusIconProps) {
  return (
    <span data-testid={testId || (isSet ? "set-indicator" : "unset-indicator")}>
      <SuccessIcon
        className={cn(
          "h-4 w-4",
          isSet
            ? "text-foreground-tertiary"
            : "text-foreground-tertiary opacity-50",
        )}
      />
    </span>
  );
}

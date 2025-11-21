import { LucideIcon } from "lucide-react";
import { cn } from "#/utils/utils";

interface ActionSummaryItemProps {
  summary: string;
  StatusIcon: LucideIcon;
  statusColor: string;
  shouldAnimate: boolean;
  isError: boolean;
  onClick?: () => void;
}

export function ActionSummaryItem({
  summary,
  StatusIcon,
  statusColor,
  shouldAnimate,
  isError,
  onClick,
}: ActionSummaryItemProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 py-0.5 px-2 rounded-md transition-all duration-200",
        "hover:bg-white/5 cursor-default",
        onClick && "cursor-pointer",
      )}
      onClick={onClick}
    >
      <StatusIcon
        className={cn(
          "w-3.5 h-3.5 shrink-0",
          statusColor,
          shouldAnimate && "animate-spin",
        )}
      />
      <span
        className={cn(
          "text-xs font-medium",
          isError ? "text-danger" : "text-foreground-secondary",
        )}
      >
        {summary}
      </span>
    </div>
  );
}

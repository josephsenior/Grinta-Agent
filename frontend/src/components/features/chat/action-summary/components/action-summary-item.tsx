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
        "flex items-center gap-2 py-1 px-2 rounded transition-all duration-150",
        "hover:bg-[#2a2d2e] cursor-default",
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
          isError ? "text-[#f48771]" : "text-[#cccccc]",
        )}
      >
        {summary}
      </span>
    </div>
  );
}

import { Tooltip } from "@heroui/react";

interface TrajectoryActionButtonProps {
  testId?: string;
  onClick: () => void;
  icon: React.ReactNode;
  tooltip?: string;
}

export function TrajectoryActionButton({
  testId,
  onClick,
  icon,
  tooltip,
}: TrajectoryActionButtonProps) {
  // Use aria-label fallback to tooltip for accessibility
  const ariaLabel = tooltip || testId || "action";

  const button = (
    <button
      type="button"
      data-testid={testId}
      aria-label={ariaLabel}
      onClick={onClick}
      className="inline-flex items-center justify-center p-2 rounded-lg bg-white/6 text-foreground hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-yellow-400 transition"
    >
      {/* Ensure icon inherits text color and consistent sizing */}
      <span className="w-4 h-4 text-inherit flex items-center justify-center">
        {icon}
      </span>
    </button>
  );

  if (tooltip) {
    return (
      <Tooltip content={tooltip} closeDelay={100}>
        {button}
      </Tooltip>
    );
  }

  return button;
}

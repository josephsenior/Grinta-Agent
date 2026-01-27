import { NavLink } from "react-router-dom";
import { cn } from "#/utils/utils";
import { BetaBadge } from "./beta-badge";
import { LoadingSpinner } from "../shared/loading-spinner";

interface NavTabProps {
  to: string;
  label: string | React.ReactNode;
  icon: React.ReactNode;
  isBeta?: boolean;
  isLoading?: boolean;
  rightContent?: React.ReactNode;
}

export function NavTab({
  to,
  label,
  icon,
  isBeta,
  isLoading,
  rightContent,
}: NavTabProps) {
  return (
    <NavLink
      end
      key={to}
      to={to}
      className={cn(
        "relative px-4 py-2 flex-1 group transition-all duration-300",
        "first-of-type:rounded-tl-2xl last-of-type:rounded-tr-2xl",
        "flex items-center gap-3 h-full min-h-[42px]",
        "hover:bg-black/30",
        "border-r border-violet-500/10 last-of-type:border-r-0",
      )}
    >
      {({ isActive }) => (
        <>
          {/* Active tab indicator */}
          {isActive && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-violet-500 to-violet-400 rounded-full" />
          )}

          {/* Tab content */}
          <div className="flex items-center justify-between w-full relative z-10">
            <div className="flex items-center gap-2 min-w-0">
              <div
                className={cn(
                  "transition-all duration-300 group-hover:scale-105",
                  isActive
                    ? "text-violet-500 drop-shadow-[0_0_6px_rgba(139,92,246,0.5)]"
                    : "text-foreground-secondary group-hover:text-violet-400",
                )}
              >
                {icon}
              </div>
              <span
                className={cn(
                  "truncate font-medium transition-all duration-300",
                  isActive
                    ? "text-white font-semibold"
                    : "text-foreground-secondary group-hover:text-foreground",
                )}
              >
                {label}
              </span>
              {isBeta && (
                <div className="animate-pulse">
                  <BetaBadge />
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {rightContent}
              {isLoading && (
                <div className="animate-spin">
                  <LoadingSpinner size="small" />
                </div>
              )}
            </div>
          </div>

          {/* Subtle hover glow effect */}
          <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-t-2xl" />
        </>
      )}
    </NavLink>
  );
}

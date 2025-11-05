import LoadingSpinnerOuter from "#/icons/loading-outer.svg?react";
import { cn } from "#/utils/utils";

interface LoadingSpinnerProps {
  size?: "xs" | "small" | "medium" | "large" | "xl";
  variant?: "default" | "dots" | "pulse" | "bars";
  className?: string;
  color?: "primary" | "secondary" | "success" | "warning" | "danger";
}

export function LoadingSpinner({
  size = "medium",
  variant = "default",
  className,
  color = "primary",
}: LoadingSpinnerProps) {
  const sizeClasses = {
    xs: "w-4 h-4",
    small: "w-6 h-6",
    medium: "w-8 h-8",
    large: "w-12 h-12",
    xl: "w-16 h-16",
  };

  const colorClasses = {
    primary: "text-brand-500",  /* Updated to violet brand */
    secondary: "text-text-secondary",
    success: "text-success-DEFAULT",
    warning: "text-warning-DEFAULT",
    danger: "text-danger-DEFAULT",
  };

  if (variant === "dots") {
    return (
      <div
        data-testid="loading-dots"
        className={cn("flex space-x-1", className)}
      >
        {([0, 1, 2] as const).map((i) => {
          const dotSizeMap: Record<string, string> = {
            xs: "w-1 h-1",
            small: "w-1.5 h-1.5",
            medium: "w-2 h-2",
            large: "w-2.5 h-2.5",
            xl: "w-3 h-3",
          };
          const dotSizeClass = dotSizeMap[size] || dotSizeMap.medium;

          return (
            <div
              key={i}
              className={cn(
                "rounded-full animate-pulse",
                colorClasses[color],
                dotSizeClass,
              )}
              style={{ animationDelay: `${i * 0.2}s`, animationDuration: "1s" }}
            />
          );
        })}
      </div>
    );
  }

  if (variant === "pulse") {
    return (
      <div
        data-testid="loading-pulse"
        className={cn(
          "rounded-full animate-pulse",
          colorClasses[color],
          sizeClasses[size],
          className,
        )}
      />
    );
  }

  if (variant === "bars") {
    return (
      <div
        data-testid="loading-bars"
        className={cn("flex space-x-1", className)}
      >
        {([0, 1, 2, 3] as const).map((i) => {
          const barSizeMap: Record<string, string> = {
            xs: "w-1 h-3",
            small: "w-1 h-4",
            medium: "w-1.5 h-6",
            large: "w-2 h-8",
            xl: "w-2.5 h-10",
          };
          const barSizeClass = barSizeMap[size] || barSizeMap.medium;

          return (
            <div
              key={i}
              className={cn("animate-pulse", colorClasses[color], barSizeClass)}
              style={{
                animationDelay: `${i * 0.1}s`,
                animationDuration: "1.2s",
              }}
            />
          );
        })}
      </div>
    );
  }

  // Default spinner - Enhanced with Cursor-style polish
  const sizeStyle = sizeClasses[size];

  return (
    <div
      data-testid="loading-spinner"
      className={cn("relative", sizeStyle, className)}
    >
      <div
        className={cn(
          "rounded-full border-4 border-border-primary/40 absolute",
          "shadow-lg shadow-brand-500/15",  /* Subtle violet glow */
          sizeStyle,
        )}
      />
      <LoadingSpinnerOuter
        className={cn(
          "absolute animate-spin",
          colorClasses[color],
          "drop-shadow-lg filter transition-all duration-300",
          "opacity-90",  /* Slightly transparent for softer feel */
          sizeStyle,
        )}
        style={{
          filter: 'drop-shadow(0 0 8px rgba(139, 92, 246, 0.3))'  /* Enhanced glow */
        }}
      />
    </div>
  );
}
